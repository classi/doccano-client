import os
import typing

from urllib.parse import urljoin

import requests


class _Router:
    """
    Provides generic `get` and `post` methods. Implemented by DoccanoClient.
    """

    def get(
        self,
        endpoint: str,
        params: dict = {},
    ) -> requests.models.Response:
        """
        Args:
            endpoint (str): An API endpoint to query.

        Returns:
            requests.models.Response: The request response (JSON).
        """
        request_url = urljoin(self.baseurl, endpoint)
        return self._get(request_url, params=params).json()

    def get_file(
            self,
            endpoint: str,
            params: dict = {},
            headers: dict = {},
            ) -> requests.models.Response:
        """
        Gets a file.
        """
        request_url = urljoin(self.baseurl, endpoint)
        return self._get(request_url, params=params, headers=headers)

    def _get(
            self,
            url: str,
            params: dict = {},
            headers: dict = {},
            ) -> requests.models.Response:
        return self.session.get(url, params=params, headers=headers)

    def post(
            self,
            endpoint: str,
            data: dict = {},
            json: dict = {},
            files: dict = {},
            headers: typing.Optional[dict] = None,
            as_json=True
            ) -> requests.models.Response:
        """
        Used to POST arbitrary (form) data or explicit JSON.
        Both will have the correct Content-Type header set.
        """
        if json and data:
            return "Error: cannot have both data and json"

        request_url = urljoin(self.baseurl, endpoint)
        result = self.session.post(
                request_url, data=data, files=files, json=json, headers=headers)
        # return json if requested
        if as_json:
            return result.json()
        return result

    def delete(
            self,
            endpoint: str,
            data: typing.Optional[dict] = None,
            files: typing.Optional[dict] = None,
            headers: typing.Optional[dict] = None,
        ) -> requests.models.Response:
        """
        Deletes something at the given endpoint.
        """
        request_url = urljoin(self.baseurl, endpoint)
        return self.session.delete(request_url, data=data, files=files, headers=headers)

    def build_url_parameter(
            self,
            url_parameter: dict
            ) -> str:
        """
        Format url_parameters.

        Args:
            url_parameter (dict): Every value must be a list.

        Returns:
            A URL parameter string. Ex: `?key1=u1&key1=u2&key2=v1&...`
        """
        return ''.join(['?', '&'.join(['&'.join(['='.join(
            [tup[0], str(value)])
                    for value in tup[1]]) for tup in url_parameter.items()])])


class DoccanoClient(_Router):
    """
    TODO: investigate alternatives to plaintext login

    Args:
        baseurl (str): The baseurl of a Doccano instance.
        username (str): The Doccano username to use for the client session.
        password (str): The respective username's password.

    Returns:
        An authorized client instance.
    """
    def __init__(self, baseurl: str, username: str, password: str):
        self.baseurl = baseurl if baseurl[-1] == '/' else baseurl+'/'
        self.session = requests.Session()
        self._login(username, password)

    def _login(
        self,
        username: str,
        password: str
    ) -> requests.models.Response:
        """
        Authorizes the DoccanoClient instance.

        Args:


        Returns:
            requests.models.Response: The authorization request response.
        """
        url = 'v1/auth/login/'
        auth = {'username': username, 'password': password}
        response = self.post(url, auth)
        self._set_csrf_header()
        return response

    def _set_csrf_header(self):
        """
        Sets the CSRF token required for the POST
        requests.

        NB: this function has to be called
        after the login endpoint.
        Even if it's the post endpoint too it doesn't require
        CSRF verification, but the token can be received from the cookies
        """
        csrf = self.session.cookies.get('csrftoken')
        self.session.headers['X-CSRFToken'] = csrf

    def get_me(self) -> requests.models.Response:
        """
        Gets this account information.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get('v1/me')

    def get_features(self) -> requests.models.Response:
        """
        Gets features.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get('v1/features')

    def get_project_list(self) -> requests.models.Response:
        """
        Gets projects list.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get('v1/projects')

    def create_project(
            self,
            name: str,
            description: str = "",
            project_type: str = "DocumentClassification",
            guideline: str = "",
            resourcetype: str = "TextClassificationProject",
            randomize_document_order: bool = False,
            collaborative_annotation: bool = False
            ) -> requests.models.Response:
        """
        Creates a new project.

        Returns:
            requests.models.Response: The request response.
        """
        payload = {
                "name": name,
                "description": description,
                "project_type": project_type,
                "guideline": guideline,
                "resourcetype": resourcetype,
                "randomize_document_order": randomize_document_order,
                "collaborative_annotation": collaborative_annotation
                }
        return self.post('v1/projects', data=payload)

    def create_document(
            self,
            project_id: int,
            text: str,
            annotations: list = [],
            annotation_approver: str = None
            ) -> requests.models.Response:
        """
        Creates a document.

        Args:
          project_id (int): project identifier
          text (str): your text
          annotations (list): annotations
          annotation_approver (str): account that approved

        Returns:
            requests.models.Response: The request response
        """
        url = 'v1/projects/{}/docs'.format(project_id)
        data = {'text': text,
                'annotations': annotations,
                'annotation_approver': annotation_approver}
        return self.post(url, data=data)

    def delete_document(
            self,
            project_id: int,
            document_id: int,
            ) -> requests.models.Response:
        url = 'v1/projects/{}/docs/{}'.format(project_id, document_id)
        return self.delete(url)

    def create_label(
            self,
            project_id: int,
            text: str,
            text_color: str = "#ffffff",
            background_color: str = "#cdcdcd",
            prefix_key: str = None,
            suffix_key: str = None
            ) -> requests.models.Response:
        """
        Creates a label to be used for annotating a document.
        """
        url = 'v1/projects/{}/labels'.format(project_id)
        label_payload = {
            "projectId": project_id,
            "text": text,
            "prefix_key": prefix_key,
            "suffix_key": suffix_key,
            "background_color": background_color,
            "text_color": text_color
        }

        try:
            return self.post(url, data=label_payload)
        except Exception as e:
            return "Failed (duplicate?): {}".format(e)

    def add_annotation(
            self,
            project_id: int,
            annotation_id: int,
            document_id: int,
            **kwargs
            ) -> requests.models.Response:
        """
        Adds an annotation to a given document.

        Variable keyword arguments \*\*kwargs give support to doccano
        annotations for different project types.

        For example, for SequenceLabeling one should call using start_offset
        and end_offset keyword arguments.

        Args:
            project_id (int): Project database identifier.
            annotation_id (int): Annotation identifier.
            document_id (int): Document identifier.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            requests.models.Response: The request response.
        """
        url = '/v1/projects/{p_id}/docs/{d_id}/annotations'.format(
                p_id=project_id,
                d_id=document_id)
        payload = {
            "label": annotation_id,
            "projectId": project_id,
            **kwargs}
        return self.post(url, json=payload)

    def get_user_list(self) -> requests.models.Response:
        """
        Gets user list.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get('v1/users')

    def get_roles(self) -> requests.models.Response:
        """
        Gets available Doccano user roles.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get('v1/roles')

    def get_project_detail(
        self,
        project_id: int
    ) -> requests.models.Response:
        """
        Gets details of a specific project.

        Args:
            project_id (int): A project ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}'.format(
                project_id=project_id
            )
        )

    def get_project_statistics(
        self,
        project_id: int
    ) -> requests.models.Response:
        """
        Gets project statistics.

        Args:
            project_id (int): A project ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/statistics'.format(
                project_id=project_id
            )
        )

    def get_label_list(
        self,
        project_id: int
    ) -> requests.models.Response:
        """
        Gets a list of labels in a given project.

        Args:
            project_id (int): A project ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/labels'.format(
                project_id=project_id
            )
        )

    def get_label_detail(
        self,
        project_id: int,
        label_id: int
    ) -> requests.models.Response:
        """
        Gets details of a specific label.

        Args:
            project_id (int): A project ID to query.
            label_id (int): A label ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/labels/{label_id}'.format(
                project_id=project_id,
                label_id=label_id
            )
        )

    def get_document_list(
        self,
        project_id: int,
        url_parameters: dict = {}
    ) -> requests.models.Response:
        """
        Gets a list of documents in a project.

        Args:
            project_id (int):
            url_parameters (dict): `limit` and `offset`

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/docs{url_parameters}'.format(
                project_id=project_id,
                url_parameters=self.build_url_parameter(url_parameters)
            )
        )

    def get_document_detail(
        self,
        project_id: int,
        doc_id: int
    ) -> requests.models.Response:
        """
        Gets details of a given document.

        Args:
            project_id (int): A project ID to query.
            doc_id (int): A document ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/docs/{doc_id}'.format(
                project_id=project_id,
                doc_id=doc_id
            )
        )

    def get_annotation_list(
        self,
        project_id: int,
        doc_id: int
    ) -> requests.models.Response:
        """
        Gets a list of annotations in a given project and document.

        Args:
            project_id (int): A project ID to query.
            doc_id (int): A document ID to query.

        Returns:
            requests.models.Response: The request response.
        """
        return self.get(
            'v1/projects/{project_id}/docs/{doc_id}/annotations'.format(
                project_id=project_id,
                doc_id=doc_id
            )
        )

    def get_annotation_detail(
        self,
        project_id: int,
        doc_id: int,
        annotation_id: int
    ) -> requests.models.Response:
        """
        """
        return self.get(
            'v1/projects/{p_id}/docs/{d_id}/annotations/{a_id}'.format(
                p_id=project_id,
                d_id=doc_id,
                a_id=annotation_id
            )
        )

    def get_doc_download(
        self,
        project_id: int,
        file_format: str = 'json',
        only_approved: bool = False
    ) -> requests.models.Response:
        """
        Downloads the dataset in specified format.
        """
        accept_headers = {
                'json': 'application/json',
                'csv': 'text/csv'
                }
        headers = {'accept': accept_headers[file_format]}

        return self.get_file(
            'v1/projects/{project_id}/docs/download'.format(
                project_id=project_id
            ),
            params={'q': file_format, 'onlyApproved': str(only_approved).lower()},
            headers=headers
        )

    def get_rolemapping_list(
        self,
        project_id: int,
    ) -> requests.models.Response:
        """
        """
        return self.get(
            'v1/projects/{project_id}/roles'.format(
                project_id=project_id
            )
        )

    def get_rolemapping_detail(
        self,
        project_id: int,
        rolemapping_id: int,
    ) -> requests.models.Response:
        """
        Currently broken!
        """
        return self.get(
            'v1/projets/{project_id}/roles/{rolemapping_id}'.format(
                project_id=project_id,
                rolemapping_id=rolemapping_id
            )
        )

    def post_doc_upload_binary(
        self,
        project_id: int,
        files: typing.List[typing.IO],
        column_data: str = "text",
        column_label: str = "label",
        delimiter: str  = "",
        encoding: str = "utf_8",
        format: str = "JSONL"
    ) -> dict:
        """
        Upload documents to doccano

        Args:
            project_id (int): The project id number.
            files (typing.List[typing.IO]): List of files to be uploaded
            column_data (str): Name of the column with data (text for annotation)
            column_label (str): Name of the column with labels (labels for annotation)
            delimiter (str): Delimeter for the current dataset
            encoding (str): Current file encoding
            format (str): The file format, ex: `plain`, `json`, or `conll`.

        Returns:
            requests.models.Response: The request response.
        """

        # upload files with filepond
        if not isinstance(files, (list, tuple)):
            # this check is very important
            # as file object is iterable and this function will
            # try to upload file line by line
            raise TypeError("Please provide a list with files")

        upload_ids = []
        for file_ in files:
            try:
                fp_resp = self.post("v1/fp/process/", files={"filepond": file_}, as_json=False)
                fp_resp.raise_for_status()
                upload_ids.append(fp_resp.text)
            except Exception as e:
                # revert previous uploads if we have a problem
                for upload_id in upload_ids:
                    self.delete("v1/fp/revert/", data=upload_id, headers={'Content-Type': 'text/plain'})
                raise e

        # confirm uploads and run processing
        upload_data = {
            "column_data": column_data,
            "column_label": column_label,
            "delimiter": delimiter,
            "encoding": encoding,
            "format": format,
            "uploadIds": upload_ids
        }
        return self.post("v1/projects/1/upload", json=upload_data)

    def post_doc_upload(
        self,
        project_id: int,
        file_name: str,
        file_path: str = './',
        column_data: str = "text",
        column_label: str = "label",
        delimiter: str  = "",
        encoding: str = "utf_8",
        format: str = "JSONL"
    ) -> requests.models.Response:
        """
        Uploads a file to a Doccano project.

        Args:
            project_id (int): The project id number.
            file_format (str): The file format, ex: `plain`, `json`, or
                               `conll`.
            file_name (str): The name of the file.
            file_path (str): The parent path of the file. Defaults to `./`.
            column_data (str): Name of the column with data (text for annotation)
            column_label (str): Name of the column with labels (labels for annotation)
            delimiter (str): Delimeter for the current dataset
            encoding (str): Current file encoding
            format (str): The file format, ex: `plain`, `json`, or `conll`.


        Returns:
            requests.models.Response: The request response.
        """
        return self.post_doc_upload_binary(
            project_id=project_id,
            files=[open(os.path.join(file_path, file_name), 'rb')],
            column_data=column_data,
            column_label=column_label,
            delimiter=delimiter,
            encoding=encoding,
            format=format
        )

    def post_approve_labels(
        self,
        project_id: int,
        doc_id: int
    ) -> requests.models.Response:
        """
        """
        return self.post(
            'v1/projects/{project_id}/docs/{doc_id}/approve-labels'.format(
                project_id=project_id,
                doc_id=doc_id
            )
        )

    def _get_any_endpoint(
        self,
        endpoint: str
    ) -> requests.models.Response:
        """
        """
        # project_id: int,
        # limit: int,
        # offset: int
        return self.get(endpoint)

    def exp_get_doc_list(
        self,
        project_id: int,
        limit: int,
        offset: int
    ) -> requests.models.Response:
        """
        """
        params = {'limit': limit, 'offset': offset}
        return self.get(
            'v1/projects/{project_id}/docs'.format(
                project_id=project_id,
            ),
            params
        )
