"""
Title: New Training Page
Date: 23/7/2021
Author: Chu Zhen Hao
Organisation: Malaysian Smart Factory 4.0 Team at Selangor Human Resource Development Centre (SHRDC)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np  # TEMP for table viz
from enum import IntEnum
from time import sleep
from copy import deepcopy
import streamlit as st
from streamlit import cli as stcli
from streamlit import session_state as session_state

# DEFINE Web APP page configuration
layout = 'wide'
st.set_page_config(page_title="Integrated Vision Inspection System",
                   page_icon="static/media/shrdc_image/shrdc_logo.png", layout=layout)

# >>>>>>>>>>>>>>>>>>>>>>TEMP>>>>>>>>>>>>>>>>>>>>>>>>

SRC = Path(__file__).resolve().parents[4]  # ROOT folder -> ./src
LIB_PATH = SRC / "lib"
# TEST_MODULE_PATH = SRC / "test" / "test_page" / "module"

if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))  # ./lib
else:
    pass

from path_desc import chdir_root
from core.utils.code_generator import get_random_string
from core.utils.log import log_info, log_error  # logger
from core.utils.helper import create_dataframe
import numpy as np  # TEMP for table viz
from project.project_management import Project
from project.training_management import NewTraining
from data_manager.database_manager import init_connection
from project.model_management import PreTrainedModel, Model
# >>>>>>>>>>>>>>>>>>>>>>>TEMP>>>>>>>>>>>>>>>>>>>>>>>
# initialise connection to Database
conn = init_connection(**st.secrets["postgres"])


# >>>> Variable Declaration >>>>
new_training = {}  # store
place = {}
DEPLOYMENT_TYPE = ("", "Image Classification", "Object Detection with Bounding Boxes",
                   "Semantic Segmentation with Polygons", "Semantic Segmentation with Masks")
DATA_DIR = Path.home() / '.local/share/integrated-vision-inspection-system/app_media'


class DeploymentType(IntEnum):
    Image_Classification = 1
    OD = 2
    Instance = 3
    Semantic = 4

    def __str__(self):
        return self.name

    @classmethod
    def from_string(cls, s):
        try:
            return DeploymentType[s]
        except KeyError:
            raise ValueError()


def show():

    chdir_root()  # change to root directory

    with st.sidebar.beta_container():

        st.image("resources/MSF-logo.gif", use_column_width=True)
    # with st.beta_container():
        st.title("Integrated Vision Inspection System", anchor='title')

        st.header(
            "(Integrated by Malaysian Smart Factory 4.0 Team at SHRDC)", anchor='heading')
        st.markdown("""___""")

    # ******** SESSION STATE ***********************************************************

    if "current_page" not in session_state:  # KIV
        session_state.current_page = "All Trainings"
        session_state.previous_page = "All Trainings"

    if "new_training" not in session_state:
        # TODO: query all project details
        session_state.project = Project(7)
        session_state.new_training = NewTraining(get_random_string(
            length=8), session_state.project)  # TODO move below
        # set random project ID before getting actual from Database
    session_state.project.query_all_fields()
    # ******** SESSION STATE *********************************************************

    # >>>> TRAINING SIDEBAR >>>>
    training_page_options = ("All Trainings", "New Training")
    with st.sidebar.beta_expander("Training Page", expanded=True):
        session_state.current_page = st.radio("", options=training_page_options,
                                              index=0)
    # <<<< TRAINING SIDEBAR <<<<

# >>>> New Training INFO >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Page title
    st.write("# __Add New Training__")
    dt_place, _ = st.beta_columns([3, 1])
    with dt_place:
        st.write("## __Deployment Type:__",
                 f"{session_state.project.deployment_type}")
    st.markdown("___")

    # right-align the project ID relative to the page
    id_blank, id_right = st.beta_columns([3, 1])
    id_right.write(
        f"### __Training ID:__ {session_state.new_training.id}")

    create_training_place = st.empty()
    # if layout == 'wide':
    outercol1, outercol2, outercol3 = st.beta_columns([1.5, 3.5, 0.5])
    # else:
    #     col2 = create_project_place
    # with create_project_place.beta_container():
    outercol1.write("## __Training Information :__")

    # >>>> CHECK IF NAME EXISTS CALLBACK >>>>
    def check_if_name_exist(field_placeholder, conn):
        context = ['name', session_state.name]
        if session_state.name:
            if session_state.new_training.check_if_exist(context, conn):
                field_placeholder['name'].error(
                    f"Training name used. Please enter a new name")
                sleep(1)
                log_error(f"Training name used. Please enter a new name")
            else:
                session_state.new_training.name = session_state.name
                log_info(f"Training name fresh and ready to rumble")

    outercol2.text_input(
        "Training Title", key="name", help="Enter the name of the training", on_change=check_if_name_exist, args=(place, conn,))
    place["name"] = outercol2.empty()

    # **** Training Description (Optional) ****
    description = outercol2.text_area(
        "Description (Optional)", key="desc", help="Enter the description of the training")
    if description:
        session_state.new_training.desc = description
    else:
        pass
# <<<<<<<< New Training INFO <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


# >>>>>>>> Choose Dataset >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    st.write("___")
    # include options to create new dataset on this page
    # create 2 columns for "New Data Button"
    outercol1, outercol2, outercol3, _ = st.beta_columns(
        [1.5, 1.75, 1.75, 0.5])

    outercol1.write("## __Dataset :__")

    # >>>> Right Column to select dataset >>>>
    with outercol3:
        session_state.project.datasets = session_state.project.query_project_dataset_list()
        session_state.project.dataset_name_list, session_state.project.dataset_name_id = session_state.project.get_dataset_name_list()

        session_state.new_training.dataset_chosen = st.multiselect(
            "Dataset List", key="dataset", options=session_state.project.dataset_name_list, help="Assign dataset to the project")

        # Button to create new dataset
        new_data_button = st.button("Create New Dataset")
        place["dataset_chosen"] = outercol3.empty()

        # print choosen dataset
        with place["dataset_chosen"]:
            if len(session_state.new_training.dataset_chosen) > 0:
                st.write("### Dataset choosen:")
                for idx, data in enumerate(session_state.new_training.dataset_chosen):
                    st.write(f"{idx+1}. {data}")
            elif len(session_state.new_training.dataset_chosen) == 0:
                st.info("No dataset selected")
    # <<<< Right Column to select dataset <<<<

    # >>>> Left Column to show full list of dataset and selection >>>>
    if "dataset_page" not in session_state:
        session_state.dataset_page = 0

    def next_page():
        session_state.dataset_page += 1

    def prev_page():
        session_state.dataset_page -= 1

    with outercol2:
        start = 10 * session_state.dataset_page
        end = start + 10

        df = session_state.project.create_dataset_dataframe()

        def highlight_row(x, selections):

            if x.Name in selections:

                return ['background-color: #90a4ae'] * len(x)
            else:
                return ['background-color: '] * len(x)
        df_slice = df.iloc[start:end]
        styler = df_slice.style.format(
            {
                "Date/Time": lambda t: t.strftime('%Y-%m-%d %H:%M:%S')

            }
        )

        # >>>>DATAFRAME
        st.table(styler.apply(
            highlight_row, selections=session_state.new_training.dataset_chosen, axis=1).set_properties(**{'text-align': 'center'}).set_table_styles(
                [dict(selector='th', props=[('text-align', 'center')])]))
    # <<<< Left Column to show full list of dataset and selection <<<<

    # >>>> Dataset Pagination >>>>
    _, col1, _, col2, _, col3, _ = st.beta_columns(
        [1.5, 0.15, 0.5, 0.45, 0.5, 0.15, 2.25])
    num_dataset_per_page = 10
    num_dataset_page = len(
        session_state.project.dataset_name_list) // num_dataset_per_page
    # st.write(num_dataset_page)
    if num_dataset_page > 1:
        if session_state.dataset_page < num_dataset_page:
            col3.button(">", on_click=next_page)
        else:
            col3.write("")  # this makes the empty column show up on mobile

        if session_state.dataset_page > 0:
            col1.button("<", on_click=prev_page)
        else:
            col1.write("")  # this makes the empty column show up on mobile

        col2.write(
            f"Page {1+session_state.dataset_page} of {num_dataset_page}")
    # <<<< Dataset Pagination <<<<
    place["dataset"] = st.empty()  # TODO :KIV
# <<<<<<<< Choose Dataset <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# >>>>>>>> Model >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    st.write("___")
    outercol1, outercol2, outercol3, _ = st.beta_columns(
        [1.5, 1.75, 1.75, 0.5])

    if 'pt_model' not in session_state:
        session_state.pt_model = PreTrainedModel()
        session_state.model = Model()

    outercol1.write("## __Deep Learning Model Selection :__")

    # ***********FRAMEWORK LIST *****************************************************************************
    framework_list = [framework.Name for framework in deepcopy(
        session_state.new_training.get_framework_list())]
    framework_list.insert(0, "")
    framework = outercol2.selectbox("Select Deep Learning Framework", options=framework_list,
                                    format_func=lambda x: 'Select a framework' if x == "" else x)
    session_state.new_training.framework = framework if framework else None
    # ***********FRAMEWORK LIST *****************************************************************************
    model_upload_select = outercol2.radio("",
                                          options=["Pre-trained Models", "Project Models", "User Custom Deep Learning Model Upload"], key='model_selection')

    # empty() placeholder to dynamically display file upload if checkbox selected
    place["model_selection"] = outercol2.empty()

    # >>>>>>>>>>>> MODEL UPLOAD >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    if model_upload_select == 'User Custom Deep Learning Model Upload':
        model = place["model_selection"].file_uploader("User Custom Model Upload", type=[
            'zip', 'tar.gz', 'tar.bz2', 'tar.xz'], key='user_custom_upload')
        if model:
            session_state.new_training.model_selected = deepcopy(
                model)  # store in model attribute
            st.write(model)  # TODO
    # >>>>>>>>>>>> MODEL UPLOAD >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    elif model_upload_select == 'Pre-trained Models':

        pre_trained_models, pt_column_names = session_state.pt_model.query_PT_table()
        pt_name_list = [
            pt.Name for pt in pre_trained_models if pt.Framework == framework]  # List to get DL model name based on framework

        # **********************************************************************************
        # >>>>RIGHT: Pre-trained models selection >>>>
        pt_name_list.insert(0, "")
        try:
            model_selection = outercol2.selectbox(
                "", options=pt_name_list, key='pre_trained_models', format_func=lambda x: 'Select a Model' if x == "" else x)
        except ValueError as e:
            pass
        # <<<<RIGHT: Pre-trained models selection <<<<

        session_state.new_training.model_selected = model_selection if model_selection else None

        # >>>>LEFT: Pre-trained models dataframe >>>>
        if "pt_page" not in session_state:
            session_state.pt_page = 0

        def next_pt_page():
            session_state.pt_page += 1

        def prev_pt_page():
            session_state.pt_page -= 1
        with outercol3:
            start = 10 * session_state.pt_page
            end = start + 10

            df = create_dataframe(pre_trained_models, pt_column_names)
            df_loc = df.loc[(df["Framework"] == session_state.new_training.framework),
                            "ID":"Framework"] if framework else df.loc[:, "ID":"Framework"]
            df_slice = df_loc.iloc[start:end]
            if session_state.new_training.model_selected:
                def highlight_row(x, selections):

                    if x.Name in selections:

                        return ['background-color: #90a4ae'] * len(x)
                    else:
                        return ['background-color: '] * len(x)

                styler = df_slice.style.apply(
                    highlight_row, selections=session_state.new_training.model_selected, axis=1)
            else:
                styler = df_slice.style
            st.table(styler.set_properties(**{'text-align': 'center'}).set_table_styles(
                [dict(selector='th', props=[('text-align', 'center')])]))

        # >>>> Dataset Pagination >>>>

        _, _, col1, _, col2, _, col3, _ = st.beta_columns(
            [1.5, 1.75, 0.15, 0.5, 0.45, 0.5, 0.15, 0.5])
        num_data_per_page = 10
        num_data_page = len(
            pre_trained_models) // num_data_per_page
        # st.write(num_dataset_page)
        if num_data_page > 1:
            if session_state.pt_page < num_data_page:
                col3.button(">", on_click=next_pt_page)
            else:
                col3.write("")  # this makes the empty column show up on mobile

            if session_state.pt_page > 0:
                col1.button("<", on_click=prev_pt_page)
            else:
                col1.write("")  # this makes the empty column show up on mobile

            col2.write(f"Page {1+session_state.pt_page} of {num_data_page}")
        # <<<< Dataset Pagination <<<<

        # <<<<LEFT: Pre-trained models dataframe <<<<

        # **********************************************************************************

    else:

        project_models, project_model_column_names = session_state.model.query_model_table()
        if project_models:
            project_model_name_list = [
                m.Name for m in project_models if m.Framework == framework]  # List to get DL model name based on framework
            project_model_name_list.insert(0, "")
        else:
            project_model_name_list = []
        # **********************************************************************************
        # >>>>RIGHT: Project models selection >>>>

        try:
            model_selection = outercol2.selectbox(
                "", options=project_model_name_list, key='project_models', format_func=lambda x: 'Select a Model' if x == "" else x)
        except ValueError as e:
            pass
        # <<<<RIGHT: Project models selection <<<<

        session_state.new_training.model_selected = model_selection if model_selection else None

        # >>>>LEFT: Pre-trained models dataframe >>>>
        if "model_page" not in session_state:
            session_state.model_page = 0

        def next_model_page():
            session_state.model_page += 1

        def prev_model_page():
            session_state.model_page -= 1
        with outercol3:
            start = 10 * session_state.model_page
            end = start + 10
            if project_models:
                df = create_dataframe(
                    project_models, project_model_column_names)
                df_loc = df.loc[(df["Framework"] == session_state.new_training.framework),
                                "ID":"Framework"] if framework else df.loc[:, "ID":"Framework"]
                df_slice = df_loc.iloc[start:end]
                if session_state.new_training.model_selected:
                    def highlight_row(x, selections):

                        if x.Name in selections:

                            return ['background-color: #90a4ae'] * len(x)
                        else:
                            return ['background-color: '] * len(x)

                    styler = df_slice.style.apply(
                        highlight_row, selections=session_state.new_training.model_selected, axis=1)
                else:
                    styler = df_slice.style
                st.table(styler.set_properties(**{'text-align': 'center'}).set_table_styles(
                    [dict(selector='th', props=[('text-align', 'center')])]))
            else:
                st.error(
                    "No Project Deep Learning Models available. Please choose from the list of Pre-trained Models or Upload your own Deep Learning Model")

        # >>>> Dataset Pagination >>>>
        if project_models:
            _, _, col1, _, col2, _, col3, _ = st.beta_columns(
                [1.5, 1.75, 0.15, 0.5, 0.45, 0.5, 0.15, 0.5])
            num_data_per_page = 10
            num_data_page = len(
                project_models) // num_data_per_page
            # st.write(num_dataset_page)
            if num_data_page > 1:
                if session_state.model_page < num_data_page:
                    col3.button(">", on_click=next_model_page)
                else:
                    # this makes the empty column show up on mobile
                    col3.write("")

                if session_state.model_page > 0:
                    col1.button("<", on_click=prev_model_page)
                else:
                    # this makes the empty column show up on mobile
                    col1.write("")

                col2.write(
                    f"Page {1+session_state.model_page} of {num_data_page}")
    place["model"] = outercol2.empty()  # TODO :KIV

    # >>>>>>>>>>>>>>>>>>WARNING>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    if not session_state.new_training.model_selected:

        place["model"].info("No Deep Learning Model selected")

    else:
        place["model"].write(
            f"### **Deep Learning Model selected:** {session_state.new_training.model_selected} ")


# <<<<<<<< Model <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

# >>>>>>>> Training Configuration >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    st.write("___")
    DATASET_LIST = []
    # **** Image Augmentation (Optional) ****
    outercol1, outercol2, outercol3, _ = st.beta_columns(
        [1.5, 1.75, 1.75, 0.5])
    outercol1.write("## __Image Augmentation :__")
    session_state.new_training.augmentation = outercol2.multiselect(
        "Augmentation List", key="augmentation", options=DATASET_LIST, format_func=lambda x: 'Select an option' if x == '' else x, help="Select the type of deployment of the project")
    place["augmentation"] = st.empty()
    outercol3.error("# WIP")
    # **** Training Parameters (Optional) ****
    st.write("___")
    outercol1, outercol2, outercol3, _ = st.beta_columns(
        [1.5, 1.75, 1.75, 0.5])
    outercol1.write("## __Training Parameters :__")
    session_state.new_training.training_param = outercol2.multiselect(
        "Training Parameters", key="training_param", options=DATASET_LIST, format_func=lambda x: 'Select an option' if x == '' else x, help="Select the type of deployment of the project")
    place["training_param"] = st.empty()
    outercol3.error("# WIP")
# >>>>>>>> Training Configuration >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # **** Submit Button ****
    success_place = st.empty()
    field = [session_state.new_training.name,
             session_state.new_training.dataset_chosen, session_state.new_training.model_selected]
    st.write(field)
    col1, col2 = st.beta_columns([3, 0.5])
    submit_button = col2.button("Submit", key="submit")

    if submit_button:
        session_state.new_training.has_submitted = session_state.new_training.check_if_field_empty(
            field, field_placeholder=place)

        if session_state.new_training.has_submitted:
            if session_state.new_project.initialise_project():
                session_state.new_editor.project_id = session_state.new_project.id
                if session_state.new_editor.init_editor():
                    success_place.success(
                        f"Successfully stored **{session_state.new_project.name}** project information in database")
                else:
                    success_place.error(
                        f"Failed to stored **{session_state.new_editor.name}** editor config in database")

            else:
                success_place.error(
                    f"Failed to stored **{session_state.new_project.name}** project information in database")

    col1, col2 = st.beta_columns(2)
    col1.write(vars(session_state.project))
    col2.write(vars(session_state.new_training))


def main():
    show()


if __name__ == "__main__":
    if st._is_running_with_streamlit:

        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
