"""
Title: User Management
Date: 25/6/2021
Author: Chu Zhen Hao
Organisation: Malaysian Smart Factory 4.0 Team at Selangor Human Resource Development Centre (SHRDC)
"""

import sys
from pathlib import Path
from enum import IntEnum
from typing import Any, Dict, List, NamedTuple, Tuple, Union
import psycopg2
from passlib.hash import argon2
from datetime import datetime
import streamlit as st
from streamlit import cli as stcli  # Add CLI so can run Python script directly
from streamlit import session_state
from core.utils.form_manager import check_if_exists, reset_page_attributes

SRC = Path(__file__).resolve().parents[2]  # ROOT folder -> ./src
LIB_PATH = SRC / "lib"

if str(LIB_PATH) not in sys.path:
    sys.path.insert(0, str(LIB_PATH))  # ./lib
else:
    pass

# >>>> User-defined Modules >>>>
from core.utils.log import logger
from data_manager.database_manager import db_fetchall, init_connection, db_fetchone, db_no_fetch


conn = init_connection(**st.secrets["postgres"])


class LoginPagination(IntEnum):
    Login = 0
    Activation = 1

    def __str__(self):
        return self.name

    @classmethod
    def from_string(cls, s):
        try:
            return LoginPagination[s]
        except KeyError:
            raise ValueError()


# must follow the names defined in database 'users' table
USER_ROLES = ("Administrator", "Developer 1 (Deployment)",
              "Developer 2 (Model Training)", "Annotator")


class UserRole(IntEnum):
    # must follow the order in 'users' table
    Administrator = 1
    Developer1 = 2
    Developer2 = 3
    Annotator = 4

    def __str__(self):
        return self.name

    @property
    def fullname(self) -> str:
        return USER_ROLES[self.value - 1]

    @staticmethod
    def get_enum_from_fullname(fullname: str) -> IntEnum:
        for enum_obj in UserRole:
            if enum_obj.fullname == fullname:
                return enum_obj
        else:
            raise ValueError(
                f"'{fullname}' is not a valid full name for user roles.")

    @staticmethod
    @st.experimental_memo
    def get_enum2fullnames() -> Dict[IntEnum, str]:
        return {enum_obj: USER_ROLES[i]
                for i, enum_obj in enumerate(UserRole)}

    @classmethod
    def from_string(cls, s):
        try:
            return UserRole[s]
        except KeyError:
            raise ValueError()


class AccountStatus(IntEnum):  # User Status
    NEW = 1  # Pending account activation
    ACTIVE = 2  # Account activated
    LOCKED = 3  # Account locked
    LOGGED_IN = 4  # Account logged-in
    LOGGED_OUT = 5  # Account logged-out

    def __str__(self):
        return self.name

    @classmethod
    def from_string(cls, s):
        try:
            return AccountStatus[s]
        except KeyError:
            raise ValueError()

    @staticmethod
    def get_all_status() -> List[str]:
        return [s.name for s in AccountStatus]

# TODO: move to form_manager


def check_if_field_empty(user_inputs: Dict[str, Any], field_placeholder, field_name):
    empty_fields = []
    # all_field_filled = all(user_inputs: Dict[str, Any])
    # if not all_field_filled:  # IF there are blank fields, iterate and produce error message
    for key, value in user_inputs.items():
        if value == "":
            field_placeholder[key].error(
                f"Please do not leave **{field_name[key]}** field blank")
            empty_fields.append(key)

    return not empty_fields


def check_if_user_exists(context: Dict[str, Any], conn) -> Tuple[bool, List[str]]:
    table = 'public.users'
    columns_with_used_values = []
    for column_name, value in context.items():
        exists_flag = check_if_exists(
            table, column_name, value, conn)
        if exists_flag:
            columns_with_used_values.append(column_name)
    return exists_flag, columns_with_used_values


def create_usertable(conn=conn):  # Create Table
    # create relation : user
    create_username_table = """
    CREATE TABLE IF NOT EXISTS public.users (
            id bigint NOT NULL GENERATED BY DEFAULT AS IDENTITY (INCREMENT 1 START 1
            MINVALUE 1
            MAXVALUE 9223372036854775807
            CACHE 1)
            , emp_id text UNIQUE
            , username text NOT NULL UNIQUE
            , first_name text
            , last_name text
            , email text
            , department text
            , position text
            , psd text NOT NULL
            , roles_id integer NOT NULL
            , status_id integer NOT NULL DEFAULT 1
            , created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
            , updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
            , last_activity timestamp with time zone
            , PRIMARY KEY (id)
        );
    """
    db_no_fetch(create_username_table, conn)

# Create User


def create_user(user, conn=conn):
    # create_usertable(conn)  # create user table if does not exist

    logger.debug("Creating user")
    psd = argon2.hash(user["psd"])
    logger.debug(f'password: {user["psd"]}')

    sql = """ 
        INSERT INTO users (
            emp_id, first_name, last_name, 
            email, department, position, 
            username, roles_id, psd)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, username, email;
    """
    roles_id = UserRole.get_enum_from_fullname(user['role']).value
    query_vars = [user["emp_id"], user["first_name"], user["last_name"],
                  user["email"], user["department"], user["position"],
                  user["username"], roles_id, psd]
    record = db_fetchone(sql, conn, query_vars)
    if record:
        logger.info(f"User created successfully with username '{record.username}' "
                    f"and email '{record.email}'")
        return True
    else:
        logger.error("Error creating user!")
        return False


# >>>> User Login

class BaseUser:
    def __init__(self) -> None:
        self.id: int = None
        self.emp_id: Union[int, str] = ''
        self.username: str = ''
        self.first_name: str = ''
        self.last_name: str = ''
        self.email: str = ''
        self.department: str = ''
        self.position: str = ''
        self.psd: str = ''
        self.role: UserRole = None
        self.account_status: AccountStatus = None
        self.session_id: int = None
# TODO: load UserLogin into User class

    def update_status(self, status: AccountStatus):
        # >>>> Update account status
        self.status = status
        update_sql = """
            UPDATE users
            SET status_id = %s
            WHERE id = %s;
        """
        update_vars = [status, self.id]
        db_no_fetch(update_sql, conn, update_vars)

    def update_psd(self):
        self.psd = argon2.hash(self.psd)

        update_query = """
            UPDATE users
            SET psd = %s,
                status_id = %s
            WHERE username = %s;
        """
        query_vars = [self.psd, self.status, self.username]
        db_no_fetch(update_query, conn, query_vars)

        delattr(self, 'psd')  # REMOVE password

    def save_session_log(self):
        sql_insert = """
            INSERT INTO session_log (users_id)
                VALUES (%s)
            RETURNING id;
        """
        insert_vars = [self.id]
        session_id = db_fetchone(sql_insert, conn, insert_vars).id

        # STORE session_id in user_login object
        self.session_id = session_id


class UserLogin(BaseUser):
    def __init__(self) -> None:
        super().__init__()

        # TODO:Temporary
        self.id: int = None
        self.username: str = ''
        # self.first_name
        # self.last_name
        # self.email
        # self.department
        # self.position
        self.psd: str = ''
        # self.role
        self.status: AccountStatus = None
        self.session_id: int = None
        self.attempts: int = 0

    def user_verification(self, user, conn=conn):
        """Verify user credentials

        Args:
            user (Dict): Contains username and password input
            conn (connect object, optional): psycopg2.connect object. Defaults to conn.

        Returns:
            Boolean: Login Fail/Pass
        """

        # --Testing
        # user = {}
        # user["username"] = input("Username: ")
        # user["psd"] = input("Password: ")
        logger.debug(f"Login password: {user['psd']}")
        # -----Testing

        user_query = """
            SELECT id, psd, status_id FROM users WHERE username = %s;
        """
        query_vars = [user['username']]
        user_exist = db_fetchone(user_query, conn, query_vars)
        logger.debug(user_exist)

        if user_exist is not None:  # if user exists
            self.id = user_exist.id
            self.psd = user_exist.psd
            self.status = AccountStatus(user_exist.status_id)
            self.username = user['username']
            # std_log(f"Retrieved password: {psd}")

            # compare password with hash
            input_password = user.pop('psd')
            verification = argon2.verify(input_password, self.psd)
            delattr(self, 'psd')  # REMOVE password
            self.attempts += 1  # INCREMENT login attempts counter

            # LOCK account if more than 3 password attempts
            if self.attempts > 3:
                self.update_status(AccountStatus["LOCKED"])

            # returns True if MATCH
            # returns False if NOT MATCH
            return verification

        elif user_exist is None:
            # User does not exist in database
            # return False if user does not exist in database
            return False


class User(BaseUser):
    def __init__(self, id) -> None:
        super().__init__()
        # TODO: To remove this method of init User class object -- no, keep it for debugging
        self.id = id
        self.query_user()

    @classmethod
    def from_user_login(cls, user_login: UserLogin):
        user = cls(user_login.id)
        user.session_id = user_login.session_id
        return user

    def query_user(self):
        query_user_SQL = """
                        SELECT
                            emp_id,
                            username,
                            first_name,
                            last_name,
                            email,
                            department,
                            position,
                            (
                                SELECT
                                    r.name
                                FROM
                                    public.roles r
                                WHERE
                                    r.id = roles_id) AS "Role",
                            (
                                SELECT
                                    x.name
                                FROM
                                    public.account_status x
                                WHERE
                                    x.id = status_id) AS "Account Status"
                        FROM
                            public.users
                        WHERE
                            id = %s;
                        """
        query_user_vars = [self.id]
        query_return = db_fetchone(query_user_SQL, conn, query_user_vars)
        if query_return:
            self.emp_id, self.username, self.first_name, \
                self.last_name, self.email, self.department, \
                self.position, role_fullname, account_status = query_return
            self.role = UserRole.get_enum_from_fullname(role_fullname)
            self.account_status = AccountStatus.from_string(account_status)
            current_timestamp = datetime.now()
            update_last_activity_SQL = """
                                    UPDATE
                                        public.users
                                    SET
                                        last_activity = %s
                                    WHERE
                                        id = %s;"""
            update_last_activity_vars = [current_timestamp, self.id]
            db_no_fetch(update_last_activity_SQL, conn,
                        update_last_activity_vars)

    def update_logout_session_log(self):
        sql_update = """
            UPDATE 
                session_log
            SET
                logout_at = %s
            WHERE
                users_id = %s;
        """
        now = datetime.now()
        update_vars = [now, self.id]
        db_no_fetch(sql_update, conn, update_vars)

    def update_info(self, new_info: Dict[str, Any]):
        logger.info("Updating user information")
        hashed_psd = argon2.hash(new_info["psd"])
        logger.debug(f'password: {new_info["psd"]}')

        role = UserRole.get_enum_from_fullname(new_info['role'])

        # update everything in the instance except for 'psd'
        self.emp_id, self.username, self.first_name, \
            self.last_name, self.email, self.department, \
            self.position, self.role = (
                new_info["emp_id"], new_info["username"], new_info["first_name"],
                new_info["last_name"], new_info["email"], new_info["department"],
                new_info["position"], role)

        sql_update = """
            UPDATE
                users
            SET
                emp_id = %s,
                username = %s,
                first_name = %s,
                last_name = %s,
                email = %s,
                department = %s,
                position = %s,
                roles_id = %s,
                psd = %s
            WHERE
                id = %s;
        """
        roles_id = role.value
        update_vars = [
            new_info["emp_id"], new_info["username"], new_info["first_name"],
            new_info["last_name"], new_info["email"], new_info["department"],
            new_info["position"], roles_id, hashed_psd, self.id]
        db_no_fetch(sql_update, conn, update_vars)


def get_default_user_info() -> BaseUser:
    default_user = BaseUser()
    return default_user


def check_if_other_user_exists(
        emp_id: Union[int, str],
        username: str, current_user: User, conn) -> Tuple[bool, List[str]]:
    """This function works similarly with check_if_user_exists() but do not consider 
    the unique fields of the current existing user. This function is used when modifying
    existing user info.
    """
    sql_query = """
        SELECT *
        FROM users
        WHERE emp_id = %s
            AND username = %s
            AND id != %s;
    """
    query_vars = [str(emp_id), username, current_user.id]
    record = db_fetchone(sql_query, conn, query_vars)
    columns_with_used_values = []
    if record:
        if record.emp_id == current_user.emp_id:
            columns_with_used_values.append('emp_id')
        if record.username == current_user.username:
            columns_with_used_values.append('username')
        return True, columns_with_used_values
    return False, columns_with_used_values


def verify_password(user: User, input_password: str) -> bool:
    sql_query = """
        SELECT psd FROM users WHERE id = %s;
    """
    query_vars = [user.id]
    hashed_psd = db_fetchone(sql_query, conn, query_vars).psd
    is_correct = argon2.verify(input_password, hashed_psd)
    return is_correct


@st.cache(hash_funcs={psycopg2.extensions.connection: lambda _: None})
def query_all_admins() -> List[NamedTuple]:
    """Query all admins, just to check whether there is any Admin user available yet
    during the first launch of the application. If None, allow user to directly create
    an Admin user."""
    sql_query = f"""
        SELECT *
        FROM public.users
        WHERE roles_id = 1;
    """
    admins = db_fetchall(
        sql_query, conn, fetch_col_name=False, return_dict=False)
    return admins


def query_all_users(return_dict: bool = False,
                    for_data_table: bool = False) -> Union[List[NamedTuple], List[Dict[str, Any]]]:
    """Return values for all project

    Args:
        return_dict (bool, optional): True if results to be in Python Dictionary, else collections.namedtuple. Defaults to False.

    Returns:
        List[NamedTuple]: [description]
    """
    ID_string = "id" if for_data_table else "ID"
    sql_query = f"""
        SELECT 
            u.id                               AS "{ID_string}",
            emp_id                             AS "Employee ID",
            CONCAT(first_name, ' ', last_name) AS "Full Name",
            email                              AS "Email",
            department                         AS "Department",
            position                           AS "Position",
            r.name                             AS "Role",
            st.name                            AS "Status"
        FROM users u
            LEFT JOIN roles r on u.roles_id = r.id
            LEFT JOIN account_status st on u.status_id = st.id
        ORDER BY u.id;
    """
    users, column_names = db_fetchall(
        sql_query, conn, fetch_col_name=True, return_dict=return_dict)
    logger.info(f"Queried users from database")
    return users, column_names


def reset_login_page():
    login_attributes = ["login_pagination", "user_login"]

    reset_page_attributes(login_attributes)


# user_create = create_user()  # Create New User

# user_exist, user_entry_flag = user_login()  # Create New User


# conn.close()
