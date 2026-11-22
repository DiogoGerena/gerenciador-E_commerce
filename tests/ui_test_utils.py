from unittest.mock import patch

import streamlit as st


def auto_confirm_operations(test_case, erp_modules):
    def confirm_operation(title, summary, on_confirm, *, key):
        on_confirm()
        st.rerun()

    patcher = patch.object(
        erp_modules,
        "show_confirmation_dialog",
        side_effect=confirm_operation,
    )
    patcher.start()
    test_case.addCleanup(patcher.stop)
