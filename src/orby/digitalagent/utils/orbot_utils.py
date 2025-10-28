import numpy as np
import os
from google.cloud import storage
from pb.v1alpha1.orbot_workflow_pb2 import Workflow
from pb.v1alpha1.orbot_action_pb2 import UiState
from pb.v1alpha1.element_pb2 import Element, Rect
from pb.v1alpha1.document_pb2 import DocumentBlob
from orby.protos.fm.action_data_pb2 import ActionData, WebState, Viewport
from pymongo import MongoClient
from bson.objectid import ObjectId
from orby.digitalagent.utils import gcs_utils


class OrbotClient:
    def __init__(self):
        assert (
            "MONGO_PASSWORD" in os.environ
        ), 'Environment variable "MONGO_PASSWORD" has to be set to access MongoDB.'
        mongodb_password = os.environ["MONGO_PASSWORD"]
        self.mongo_client = MongoClient(
            f"mongodb+srv://foundation-model:{mongodb_password}@dev.ki0ac.mongodb.net/?retryWrites=true&w=majority&appName=dev"
        )
        self.db = self.mongo_client["dev"]

    def load_workflow(self, id: str) -> list[Workflow.Process]:
        """Downloads a workflow / trajectory."""
        collection = self.db["orbot_workflows"]
        document = collection.find_one({"_id": ObjectId(id)})

        results = []
        for bp in document["processes"]:
            message = Workflow.Process()
            message.ParseFromString(bp)
            results.append(message)
        return results

    def load_file(self, file_id: str) -> bytes:
        gcs_client = storage.Client()
        collection = self.db["user_files"]
        document = collection.find_one({"_id": ObjectId(file_id)})
        gcs_uri = document["path"]
        bucket, blob_name = gcs_utils.decode_gcs_uri(gcs_uri)
        return gcs_utils.download_file_from_gcs_as_bytes(gcs_client, bucket, blob_name)

    def ui_state_to_web_state(self, ui_state: UiState) -> WebState:
        root_element = Element()
        if ui_state.root_element.id:
            root_element.ParseFromString(self.load_file(ui_state.root_element.id))
        screenshot = DocumentBlob()
        if ui_state.viewport_screenshot.id:
            screenshot.content = self.load_file(ui_state.viewport_screenshot.id)
        state = WebState(
            url=ui_state.url,
            # Add the utility to populate the HTML or the dom tree here
            root_element=root_element,
            viewport=Viewport(
                viewport_rect=Rect(
                    width=ui_state.viewport_width,
                    height=ui_state.viewport_height,
                ),
                screenshot=screenshot,
            ),
        )
        return state

    def process_to_action_data(self, process: Workflow.Process) -> list[ActionData]:
        results = []
        for action in process.actions:
            action_data = ActionData(
                action=action,
                before_state=self.ui_state_to_web_state(action.before_state),
            )
            results.append(action_data)
        return results
