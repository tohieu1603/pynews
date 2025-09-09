import os
from pathlib import Path
import logging
from typing import Optional, Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

list_config_file = [
    "config/__init__.py",
    "config/settings/__init__.py",
    "config/settings/base.py",
    "config/settings/development.py",
    "config/settings/production.py",
    "config/settings/production.py",
    "config/urls.py",
    "config/wsgi.py",
    "config/asgi.py"
]

list_api_file = [
    "api/__init__.py",
    "api/main.py",
    "api/router.py",
    "api/middleware.py",
    "api/exceptions.py",
    "api/dependencies.py"
]

list_authentication_file = [
    "authentication/__init__.py",
    "authentication/models.py",
    "authentication/schemas.py",
    "authentication/api.py",
    "authentication/services.py",
    "authentication/permissions.py",
    "authentication/utils.py",
    "authentication/tests/__init__.py",
    "authentication/tests/test_api.py",
    "authentication/tests/test_schemas.py",
    "authentication/tests/test_services.py",
    "authentication/migrations/",
]

list_core_files = [
    "core/__init__.py",
    "core/authentication.py",
    "core/permissions.py", 
    "core/pagination.py",
    "core/schemas.py",
    "core/exceptions.py",
    "core/validators.py",
    "core/utils.py",
    "core/decorators.py",
    "core/constants.py",
]

list_database_files = [
    "database/__init__.py",
    "database/managers.py",
    "database/mixins.py",
    "database/fields.py",
    "database/fixtures/__init__.py",
    "database/fixtures/initial_data.json",
]

list_tests_files = [
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_integration.py",
    "tests/test_authentication.py",
    "tests/fixtures/__init__.py",
    "tests/fixtures/api_data.json",
    "tests/utils/__init__.py",
    "tests/utils/test_helpers.py",
]

list_example_files = [
    "users/__init__.py",
    "users/models.py",
    "users/schemas.py",
    "users/api.py",
    "users/services.py",
    "users/permissions.py",
    "users/filters.py",
    "users/utils.py",
    "users/tests/__init__.py",
    "users/tests/test_api.py",
    "users/tests/test_services.py",
    "users/tests/test_models.py",
    "users/tests/test_schemas.py",
    "users/tests/factories.py",
    "users/migrations/",
]

name_list_file = ["list_config_file", "list_api_file"]
name_list_file_inapps = [list_authentication_file, list_core_files, list_database_files, list_tests_files]

def create_file(files : list, prefix_path: Optional[Union[str, Path]] = None):
    for file in files: 
        file_path = Path("apps", file) if prefix_path else Path(file)
        filedir, filename = os.path.split(file_path)

        if filedir !="":
            os.makedirs(filedir, exist_ok=True)
            logging.info(f"Creating directory {filedir} for the filename {filename}")

        if (not os.path.exists(file_path)) or (os.path.getsize(file_path) == 0):
            with open(file_path, "w") as f:
                pass
                logging.info(f"Creating empty file {file_path}")

        else:
            logging.info(f"File {file_path} already exists")


if __name__=="__main__":
    create_file(list_example_files,prefix_path="apps/")
    # for file in name_list_file_inapps:
    #     create_file(file, prefix_path="apps/")
