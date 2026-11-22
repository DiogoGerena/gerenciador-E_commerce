import logging
import unittest
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest

import app.erp_modules as erp_modules
from tests.ui_test_utils import auto_confirm_operations


USER = {
    "id": 17,
    "name": "Pessoa Usuária",
    "email": "pessoa@example.test",
    "role": "aux.ecommerce",
    "created_at": "2026-11-21T12:00:00Z",
}


class UserManagementScreenTests(unittest.TestCase):
    def setUp(self):
        auto_confirm_operations(self, erp_modules)

    @staticmethod
    def _render(user, token="admin-session"):
        app = AppTest.from_string(
            "import app.erp_modules as erp_modules\n"
            "erp_modules.render_usuarios()"
        )
        app.session_state["auth_user"] = user
        if token is not None:
            app.session_state["auth_token"] = token
        return app.run()

    @staticmethod
    def _fill_and_submit(app, *, password="LocalOnly9", role="Adm"):
        app.text_input[0].set_value("Pessoa Usuária")
        app.text_input[1].set_value("pessoa@example.test")
        app.text_input[2].set_value(password)
        app.selectbox[0].set_value(role)
        return app.form_submit_button(key="usuarios_admin_submit_0").click().run()

    def test_operational_and_nonexact_admin_profiles_cannot_open_page(self):
        for profile in ("aux.ecommerce", "admin", "ADM", "Adm "):
            with self.subTest(profile=profile):
                with patch.object(erp_modules, "listar_usuarios") as list_users:
                    with patch.object(erp_modules, "criar_usuario") as create_user:
                        app = self._render({"profile": profile})

                self.assertEqual(app.exception, [])
                self.assertTrue(
                    any(
                        "somente o perfil Adm" in element.value
                        for element in app.error
                    )
                )
                self.assertEqual(app.text_input, [])
                self.assertEqual(app.dataframe, [])
                list_users.assert_not_called()
                create_user.assert_not_called()

    def test_admin_without_session_token_cannot_call_user_endpoint(self):
        with patch.object(erp_modules, "listar_usuarios") as list_users:
            app = self._render({"profile": "Adm"}, token=None)

        self.assertEqual(app.exception, [])
        self.assertTrue(any("sessão expirou" in item.value for item in app.error))
        list_users.assert_not_called()

    def test_admin_lists_real_users_without_rendering_extra_sensitive_fields(self):
        user_with_unexpected_field = dict(USER, password="must-not-render")
        with patch.object(
            erp_modules,
            "listar_usuarios",
            return_value=[user_with_unexpected_field],
        ) as list_users:
            app = self._render({"profile": "Adm"})

        self.assertEqual(app.exception, [])
        list_users.assert_called_once_with("admin-session")
        self.assertEqual(len(app.dataframe), 1)
        columns = list(app.dataframe[0].value.columns)
        self.assertEqual(columns, ["Nome", "E-mail", "Perfil", "Criado em"])
        rendered = " ".join(str(value) for value in app.dataframe[0].value.values.flatten())
        self.assertNotIn("must-not-render", rendered)
        self.assertEqual(len(app.text_input), 3)

    def test_list_http_401_and_403_are_reported_without_exposing_response_body(self):
        cases = (
            (401, "sessão expirou"),
            (403, "negou a permissão"),
        )
        for status_code, expected_message in cases:
            with self.subTest(status_code=status_code):
                response = Mock()
                response.status_code = status_code
                response.json.return_value = {"message": "Request denied"}
                response.text = ""
                error = requests.HTTPError(response=response)
                with patch.object(
                    erp_modules,
                    "listar_usuarios",
                    side_effect=error,
                ):
                    app = self._render({"profile": "Adm"})

                self.assertEqual(app.exception, [])
                self.assertTrue(
                    any(expected_message in item.value for item in app.error)
                )

    def test_confirmed_create_sends_expected_data_clears_password_and_refreshes(self):
        created_user = dict(USER, role="Adm")
        with patch.object(
            erp_modules,
            "listar_usuarios",
            side_effect=[[], [created_user]],
        ) as list_users:
            with patch.object(
                erp_modules,
                "criar_usuario",
                return_value=created_user,
            ) as create_user:
                app = self._render({"profile": "Adm"})
                app = self._fill_and_submit(app)

        self.assertEqual(app.exception, [])
        create_user.assert_called_once_with(
            "admin-session",
            name="Pessoa Usuária",
            email="pessoa@example.test",
            password="LocalOnly9",
            role="Adm",
        )
        self.assertEqual(
            [call.args for call in list_users.call_args_list],
            [("admin-session",), ("admin-session",)],
        )
        self.assertTrue(
            any("confirmação do Xano" in item.value for item in app.success)
        )
        self.assertTrue(
            any(
                item.value.loc[0, "E-mail"] == "pessoa@example.test"
                for item in app.dataframe
            )
        )
        state_values = [str(value) for value in app.session_state.values()]
        self.assertFalse(any("LocalOnly9" in value for value in state_values))

    def test_invalid_form_is_rejected_before_post_and_clears_password(self):
        with patch.object(erp_modules, "listar_usuarios", return_value=[]):
            with patch.object(erp_modules, "criar_usuario") as create_user:
                app = self._render({"profile": "Adm"})
                app.text_input[0].set_value("Pessoa")
                app.text_input[1].set_value("invalido")
                app.text_input[2].set_value("LocalOnly9")
                app = app.form_submit_button(
                    key="usuarios_admin_submit_0"
                ).click().run()

        self.assertEqual(app.exception, [])
        create_user.assert_not_called()
        self.assertTrue(
            any("e-mail válido" in item.value for item in app.error)
        )
        self.assertFalse(
            any("LocalOnly9" in str(value) for value in app.session_state.values())
        )

    def test_duplicate_email_error_is_clear_and_never_displays_password(self):
        password = "Sensitive9"
        response = Mock()
        response.status_code = 400
        response.json.return_value = {
            "message": f"Email already exists; password: {password}"
        }
        response.text = ""
        error = requests.HTTPError(response=response)
        log_messages = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())

        root_logger = logging.getLogger()
        handler = CaptureHandler()
        root_logger.addHandler(handler)
        try:
            with patch.object(erp_modules, "listar_usuarios", return_value=[]):
                with patch.object(erp_modules, "criar_usuario", side_effect=error):
                    app = self._render({"profile": "Adm"})
                    app = self._fill_and_submit(app, password=password)
        finally:
            root_logger.removeHandler(handler)

        self.assertEqual(app.exception, [])
        self.assertTrue(any("e-mail já está cadastrado" in item.value for item in app.error))
        self.assertFalse(
            any(password in item.value for item in app.error)
            or any(password in item.value for item in app.warning)
        )
        self.assertFalse(any(password in message for message in log_messages))
        self.assertEqual(len(app.dataframe), 0)

    def test_invalid_http_400_is_not_reported_as_duplicate(self):
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"message": "Invalid role"}
        response.text = ""
        error = requests.HTTPError(response=response)
        with patch.object(erp_modules, "listar_usuarios", return_value=[]):
            with patch.object(erp_modules, "criar_usuario", side_effect=error):
                app = self._render({"profile": "Adm"})
                app = self._fill_and_submit(app)

        self.assertEqual(app.exception, [])
        self.assertTrue(
            any("rejeitou os dados do cadastro" in item.value for item in app.error)
        )
        self.assertFalse(any("já está cadastrado" in item.value for item in app.error))
        self.assertFalse(
            app.form_submit_button(key="usuarios_admin_submit_1").disabled
        )

    def test_authorization_http_errors_have_specific_messages(self):
        cases = (
            (401, "sessão expirou"),
            (403, "negou a permissão administrativa"),
        )
        for status_code, expected_message in cases:
            with self.subTest(status_code=status_code):
                response = Mock()
                response.status_code = status_code
                response.json.return_value = {"message": "Request denied"}
                response.text = ""
                error = requests.HTTPError(response=response)
                with patch.object(erp_modules, "listar_usuarios", return_value=[]):
                    with patch.object(
                        erp_modules,
                        "criar_usuario",
                        side_effect=error,
                    ):
                        app = self._render({"profile": "Adm"})
                        app = self._fill_and_submit(app)

                self.assertEqual(app.exception, [])
                self.assertTrue(
                    any(expected_message in item.value for item in app.error)
                )

    def test_http_500_blocks_retry_until_list_refresh_and_never_reposts(self):
        response = Mock()
        response.status_code = 500
        response.json.return_value = {"message": "Internal server error"}
        response.text = ""
        error = requests.HTTPError(response=response)
        with patch.object(
            erp_modules,
            "listar_usuarios",
            side_effect=[[], []],
        ) as list_users:
            with patch.object(
                erp_modules,
                "criar_usuario",
                side_effect=error,
            ) as create_user:
                app = self._render({"profile": "Adm"})
                app = self._fill_and_submit(app)

                self.assertTrue(
                    any(
                        "Não houve reenvio automático" in item.value
                        for item in app.warning
                    )
                )
                self.assertTrue(
                    app.form_submit_button(
                        key="usuarios_admin_submit_1"
                    ).disabled
                )
                self.assertEqual(list_users.call_count, 1)
                self.assertEqual(create_user.call_count, 1)
                app.button(key="usuarios_admin_refresh").click().run()

        self.assertEqual(list_users.call_count, 2)
        self.assertEqual(create_user.call_count, 1)
        self.assertFalse(
            app.form_submit_button(key="usuarios_admin_submit_1").disabled
        )

    def test_inconclusive_create_requires_successful_manual_refresh_before_retry(self):
        with patch.object(
            erp_modules,
            "listar_usuarios",
            side_effect=[[], []],
        ) as list_users:
            with patch.object(
                erp_modules,
                "criar_usuario",
                side_effect=erp_modules.OperacaoUsuarioInconclusivaError(
                    "network failure"
                ),
            ) as create_user:
                app = self._render({"profile": "Adm"})
                app = self._fill_and_submit(app)

                self.assertTrue(
                    any("Não houve reenvio automático" in item.value for item in app.warning)
                )
                self.assertTrue(
                    app.form_submit_button(
                        key="usuarios_admin_submit_1"
                    ).disabled
                )
                self.assertEqual(list_users.call_count, 1)
                self.assertEqual(create_user.call_count, 1)

                app.button(key="usuarios_admin_refresh").click().run()

        self.assertEqual(app.exception, [])
        self.assertEqual(list_users.call_count, 2)
        self.assertEqual(create_user.call_count, 1)
        self.assertFalse(
            app.form_submit_button(key="usuarios_admin_submit_1").disabled
        )


if __name__ == "__main__":
    unittest.main()
