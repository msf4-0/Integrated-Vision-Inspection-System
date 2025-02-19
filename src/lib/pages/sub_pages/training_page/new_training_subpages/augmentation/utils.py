from typing import List, Tuple
import cv2
import os
import numpy as np
import json
from imutils.paths import list_images

import streamlit as st
from streamlit import session_state

from data_manager.dataset_management import Dataset

CONFIG_PATH = "src/lib/pages/sub_pages/training_page/new_training_subpages/augmentation/augmentations.json"


@st.cache
def get_image_dir():
    # originally this function takes the image_folder from the sample image folder
    # image_folder = "src/lib/pages/sub_pages/training_page/new_training_subpages/images"
    first_project_dataset_name = session_state.project.data_name_list[0]
    image_folder = Dataset.get_dataset_path(first_project_dataset_name)
    return image_folder


@st.cache
def get_images_list(path_to_folder: str, n_images: int = 10) -> Tuple[List[str], List[str]]:
    """Return the list of images from folder
    Args:
        path_to_folder (str): absolute or relative path to the folder with images
        n_images (str): maximum number of images to display as options. 
            Set to `None` to use all images. Defaults to 10.
    """
    image_paths = sorted(list_images(path_to_folder))[:n_images]
    image_names_list = [os.path.basename(x) for x in image_paths]
    return image_names_list, image_paths


@st.cache
def get_images_list_from_masks(
        mask_folder: List[str], ori_image_folder: str) -> Tuple[List[str], List[str]]:
    image_names, image_paths = [], []
    ori_image_paths = list_images(ori_image_folder)
    mask_names_set = set(os.path.basename(p) for p in list_images(mask_folder))
    for p in ori_image_paths:
        ori_fname = os.path.basename(p)
        fname_no_ext = os.path.splitext(ori_fname)[0]
        # mask images must end with .png in this case
        mask_fname = f"{fname_no_ext}.png"
        if mask_fname in mask_names_set:
            image_names.append(ori_fname)
            image_paths.append(p)
    return image_names, image_paths


def load_image(path_to_image: str, bgr2rgb: bool = True):
    """Load the image
    Args:
        path_to_image (str): path to the image file itself
        bgr2rgb (bool): converts BGR image to RGB if True
    """
    image = cv2.imread(path_to_image)
    if bgr2rgb:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def upload_image(bgr2rgb: bool = True):
    """Upload the image
    Args:
        bgr2rgb (bool): converts BGR image to RGB if True
    """
    file = st.sidebar.file_uploader(
        "Upload your image (jpg, jpeg, or png)", ["jpg", "jpeg", "png"]
    )
    image = cv2.imdecode(np.fromstring(file.read(), np.uint8), 1)
    if bgr2rgb:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


@st.experimental_memo
def load_augmentations_config(
    placeholder_params: dict, path_to_config: str = CONFIG_PATH
) -> dict:
    """Load the json config with params of all transforms
    Args:
        placeholder_params (dict): dict with values of placeholders
        path_to_config (str): path to the json config file
    """
    with open(path_to_config, "r") as config_file:
        augmentations = json.load(config_file)
    for name, params in augmentations.items():
        params = [fill_placeholders(param, placeholder_params)
                  for param in params]
    return augmentations


def fill_placeholders(params: dict, placeholder_params: dict) -> dict:
    """Fill the placeholder values in the config file
    Args:
        params (dict): original params dict with placeholders
        placeholder_params (dict): dict with values of placeholders
    """
    # TODO: refactor
    if "placeholder" in params:
        placeholder_dict = params["placeholder"]
        for k, v in placeholder_dict.items():
            if isinstance(v, list):
                params[k] = []
                for element in v:
                    if element in placeholder_params:
                        params[k].append(placeholder_params[element])
                    else:
                        params[k].append(element)
            else:
                if v in placeholder_params:
                    params[k] = placeholder_params[v]
                else:
                    params[k] = v
        params.pop("placeholder")
    return params


def get_params_string(param_values: dict) -> str:
    """Generate the string from the dict with parameters
    Args:
        param_values (dict): dict of "param_name" -> "param_value"
    """
    params_string = ", ".join(
        [k + "=" + str(param_values[k]) for k in param_values.keys()]
    )
    return params_string


def get_placeholder_params(image):
    return {
        "image_width": image.shape[1],
        "image_height": image.shape[0],
        "image_half_width": int(image.shape[1] / 2),
        "image_half_height": int(image.shape[0] / 2),
    }


def select_transformations(augmentations: dict, interface_type: str) -> list:
    # extract names from augmentations.json
    all_transform_names = sorted(list(augmentations.keys()))

    # extracting all the data stored in our Training instance
    existing_config = session_state.new_training.augmentation_config
    aug = existing_config.augmentations
    existing_transforms = list(aug.keys())

    if existing_transforms:
        # this will only have 1 transform if `interface_type` == `Simple`
        first_transform_idx = all_transform_names.index(existing_transforms[0])
    else:
        first_transform_idx = 0

    # in the Simple mode you can choose only one transform
    if interface_type == "Simple":
        selected_transform_names = [
            st.sidebar.selectbox(
                "Select a transformation:", all_transform_names,
                index=first_transform_idx
            )
        ]
    # in the professional mode you can choose several transforms
    elif interface_type == "Professional":
        selected_transform_names = [
            st.sidebar.selectbox(
                "Select transformation №1:", all_transform_names,
                index=first_transform_idx
            )
        ]

        while selected_transform_names[-1] != "None":
            filtered_transform_names = all_transform_names.copy()
            for t in selected_transform_names:
                # to avoid duplicated transforms, also make database management much easier
                filtered_transform_names.remove(t)

            current_idx = len(selected_transform_names)
            if len(existing_transforms) > current_idx:
                selection_idx = all_transform_names.index(
                    existing_transforms[current_idx])
            else:
                selection_idx = 0

            selected_transform_names.append(
                st.sidebar.selectbox(
                    f"Select transformation №{current_idx + 1}:",
                    ["None"] + filtered_transform_names,
                    index=selection_idx
                    # key=f'aug_func_{current_idx}'
                )
            )
        selected_transform_names = selected_transform_names[:-1]
    return selected_transform_names


def show_random_params(data: dict, interface_type: str = "Professional"):
    """Shows random params used for transformation (from A.ReplayCompose)"""
    st.subheader("Random params used")
    st.markdown(
        "<p style='border: 2px solid lightgray; border-radius: 0.5em; padding: 5px'>"
        "This will show NULL value when the transformation is not applied due to the assigned "
        "probability to the associated transformation.</p>",
        unsafe_allow_html=True)
    random_values = {}
    for applied_params in data["replay"]["transforms"]:
        random_values[
            applied_params["__class_fullname__"].split(".")[-1]
        ] = applied_params["params"]
    st.write(random_values)
