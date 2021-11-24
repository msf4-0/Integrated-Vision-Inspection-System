"""
Title: Page to manage all users
Date: 24/11/2021
Author: Anson Tan Chen Tung
Organisation: Malaysian Smart Factory 4.0 Team at Selangor Human Resource Development Centre (SHRDC)


Copyright (C) 2021 Selangor Human Resource Development Centre

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. 

Copyright (C) 2021 Selangor Human Resource Development Centre
SPDX-License-Identifier: Apache-2.0
========================================================================================
"""
import sys
from pathlib import Path
import streamlit as st
from streamlit import cli as stcli  # Add CLI so can run Python script directly
from streamlit import session_state
from main_page_management import MainPagination

# >>>> User-defined Modules >>>>
from path_desc import chdir_root
from core.utils.log import logger


def main():
    logger.debug("Navigator: User Management")
    st.title("User Management")
    st.markdown("___")

    # TODO: allow reset user passwords
    # TODO: allow user deletion or role change
    def to_new_user_cb():
        session_state.main_pagination = MainPagination.CreateUser

    st.button("Create New User", key='btn_create_user',
              on_click=to_new_user_cb)


if __name__ == "__main__":
    if st._is_running_with_streamlit:
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
