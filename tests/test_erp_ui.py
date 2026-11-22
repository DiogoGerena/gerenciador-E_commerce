import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from app import erp_ui


class ConfirmationDialogTests(unittest.TestCase):
    def setUp(self):
        self.columns = (MagicMock(), MagicMock())

    def _render_dialog(self, button_results, on_confirm):
        with (
            patch.object(
                erp_ui.st,
                "dialog",
                side_effect=lambda *args, **kwargs: lambda function: function,
            ) as dialog,
            patch.object(erp_ui.st, "columns", return_value=self.columns),
            patch.object(erp_ui.st, "button", side_effect=button_results) as button,
            patch.object(erp_ui.st, "write"),
            patch.object(erp_ui.st, "markdown"),
            patch.object(erp_ui.st, "divider"),
            patch.object(erp_ui.st, "rerun"),
        ):
            erp_ui.show_confirmation_dialog(
                "Confirmar ação",
                {"Registro": "Item de teste"},
                on_confirm,
                key="test_confirmation",
            )
        return dialog, button

    def test_confirm_runs_action_only_after_confirm_button(self):
        action = MagicMock()
        dialog, button = self._render_dialog([False, True], action)

        dialog.assert_called_once_with("Confirmar ação", width="small")
        self.assertEqual(button.call_args_list[1].kwargs["key"], "test_confirmation_confirm")
        action.assert_called_once_with()

    def test_cancel_does_not_run_action(self):
        action = MagicMock()
        dialog, button = self._render_dialog([True, False], action)

        dialog.assert_called_once()
        self.assertEqual(button.call_args_list[0].kwargs["key"], "test_confirmation_cancel")
        action.assert_not_called()


class ThemeRenderingTests(unittest.TestCase):
    def test_tables_and_scroll_effects_use_light_accessible_styles(self):
        self.assertIn('[data-testid="stDataFrame"]', erp_ui.CSS)
        self.assertIn('[data-testid="stDataEditor"]', erp_ui.CSS)
        self.assertIn("--gdg-bg-cell: #FFFFFF", erp_ui.CSS)
        self.assertIn("--gdg-bg-header: #FFF1B8", erp_ui.CSS)
        self.assertIn("background: #F0F0ED", erp_ui.CSS)
        self.assertIn("overflow-x: auto", erp_ui.CSS)
        self.assertIn("animation-timeline: view()", erp_ui.CSS)
        self.assertIn("animation-timeline: scroll(root block)", erp_ui.CSS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", erp_ui.CSS)
        self.assertIn("background: #F2C94C !important", erp_ui.CSS)
        self.assertIn("background: #FFFFFF !important", erp_ui.CSS)
        self.assertIn("background: #F0F0ED !important", erp_ui.CSS)
        self.assertIn("font-weight: 600 !important", erp_ui.CSS)
        self.assertIn('[data-testid="stTextInputRootElement"]', erp_ui.CSS)
        self.assertIn('button[aria-label="Show password"]', erp_ui.CSS)
        self.assertIn("outline: 3px solid", erp_ui.CSS)
        self.assertNotIn("border-left: 4px solid var(--cb-yellow)", erp_ui.CSS)

    def test_dataframe_helper_applies_whole_row_zebra_styles(self):
        frame = pd.DataFrame({"A": [1, 2, 3, 4], "B": [5, 6, 7, 8]})
        styles = erp_ui._estilos_linhas_tabela(frame)
        expected = (
            "#FFFFFF",
            "#F0F0ED",
            "#FFFFFF",
            "#F0F0ED",
        )
        for row_position, background in enumerate(expected):
            self.assertTrue(
                all(
                    background in style
                    for style in styles.iloc[row_position].tolist()
                )
            )

        with patch.object(erp_ui.st, "dataframe") as dataframe:
            erp_ui.render_dataframe(frame, width="stretch", hide_index=True)

        styled_frame = dataframe.call_args.args[0]
        rendered_styles = styled_frame.to_html()
        self.assertIn("background-color: #FFFFFF", rendered_styles)
        self.assertIn("background-color: #F0F0ED", rendered_styles)
        dataframe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
