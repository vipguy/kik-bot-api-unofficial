#!/usr/bin/env python3
"""
A Kik bot that just logs every event that it gets (new message, message read, etc.),
and echos back whatever chat messages it receives.
"""

import yaml
import os

import kik_unofficial.datatypes.xmpp.chatting as chatting
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.errors import SignUpError, LoginError
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse
from kik_unofficial.datatypes.xmpp.sign_up import RegisterResponse, UsernameUniquenessResponse
from kik_unofficial.datatypes.xmpp.login import LoginResponse, ConnectionFailedResponse


def main():
    # The credentials file where you store the bot's login information
    creds_file = "creds.yaml"

    # Changes the current working directory to /examples
    if not os.path.isfile(creds_file):
        os.chdir("examples")

    # load the bot's credentials from creds.yaml
    with open(creds_file) as f:
        creds = yaml.safe_load(f)

    # create the bot
    bot = EchoBot(creds)

    # let the bot start
    bot.client.wait_for_messages()


class EchoBot(KikClientCallback):
    def __init__(self, creds: dict):
        username = creds["username"]
        password = creds.get("password") or input("Enter your password: ")

        # optional parameters
        device_id = creds["device_id"]
        android_id = creds["android_id"]
        node = creds.get("node")  # If you don't know it, set it to None

        self.client = KikClient(self, username, str(password), node, device_id=device_id, android_id=android_id, enable_console_logging=True)

    # Initialization and Authentication
    def on_authenticated(self):
        self.client.log.info("Now I'm Authenticated, let's request roster")
        self.client.request_roster()

    def on_login_ended(self, response: LoginResponse):
        self.client.log.info(f"Full name: {response.first_name} {response.last_name}")

    # Chat and Group Messages
    def on_chat_message_received(self, chat_message: chatting.IncomingChatMessage):
        self.client.log.info(f"'{chat_message.from_jid}' says: {chat_message.body}")
        self.client.log.info("Replaying.")
        self.client.send_chat_message(chat_message.from_jid, 'You said "' + chat_message.body + '"!')

    def on_group_message_received(self, chat_message: chatting.IncomingGroupChatMessage):
        self.client.log.info(f"'{chat_message.from_jid}' from group ID {chat_message.group_jid} says: {chat_message.body}")

    def on_image_received(self, image_message: chatting.IncomingImageMessage):
        self.client.log.info(f"Image message was received from {image_message.from_jid}")

    # Events and Statuses
    def on_message_delivered(self, response: chatting.IncomingMessageDeliveredEvent):
        self.client.log.info(f"Chat message with ID {response.message_id} is delivered.")

    def on_message_read(self, response: chatting.IncomingMessageReadEvent):
        self.client.log.info(f"Human has read the message with ID {response.message_id}.")

    def on_is_typing_event_received(self, response: chatting.IncomingIsTypingEvent):
        self.client.log.info(f'{response.from_jid} is now {"" if response.is_typing else "not "}typing.')

    def on_group_is_typing_event_received(self, response: chatting.IncomingGroupIsTypingEvent):
        self.client.log.info(f'{response.from_jid} is now {"" if response.is_typing else "not "}typing in group {response.group_jid}')

    def on_roster_received(self, response: FetchRosterResponse):
        self.client.log.info("Chat partners:\n" + "\n".join([str(member) for member in response.peers]))

    def on_peer_info_received(self, response: PeersInfoResponse):
        self.client.log.info(f"Peer info: {str(response.users)}")

    def on_group_status_received(self, response: chatting.IncomingGroupStatus):
        self.client.log.info(f"Status message in {response.group_jid}: {response.status}")

    def on_group_receipts_received(self, response: chatting.IncomingGroupReceiptsEvent):
        self.client.log.info(f'Received receipts in group {response.group_jid}: {",".join(response.receipt_ids)}')

    def on_status_message_received(self, response: chatting.IncomingStatusResponse):
        self.client.log.info(f"Status message from {response.from_jid}: {response.status}")

    def on_friend_attribution(self, response: chatting.IncomingFriendAttribution):
        self.client.log.info(f"Friend attribution request from {response.referrer_jid}")

    # Account Management
    def on_username_uniqueness_received(self, response: UsernameUniquenessResponse):
        self.client.log.info(f"Is {response.username} a unique username? {response.unique}")

    def on_sign_up_ended(self, response: RegisterResponse):
        self.client.log.info(f"Registered as {response.kik_node}")

    # Error Handling
    def on_connection_failed(self, response: ConnectionFailedResponse):
        self.client.log.error(f"Connection failed: {response.message}")

    def on_login_error(self, login_error: LoginError):
        if login_error.is_captcha():
            login_error.solve_captcha_wizard(self.client)

    def on_register_error(self, response: SignUpError):
        self.client.log.error(f"Register error: {response.message}")


if __name__ == "__main__":
    main()
