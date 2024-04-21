"""
* Welcome to Early Bird Labs
    * Visual with intro to EBL


* About EBL (Offering/Services)
* Manual customer intake form:
    * Customer Name
    * Company Name
    * Legal Entity
    * Contact Info
        * Number
        * Email
* CREATE CUSTOMER PROFILE
* Conversational company intake form:
    * Why does your company exist? What is it’s mission or core objective?
    * How does your company provide value? What does it do to fulfill the goods or services it offers?
    * What does your company do? What products or services do you offer?
* Mutual NDA and Service Agreement for general coverage
* CREATE COMPANY PROFILE
    * ATTACH CUSTOMER TO COMPANY
"""

from blockkit import (
    Message,
    Section,
    Button,
    MarkdownText,
    Actions,
    Modal,
    Input,
    PlainTextInput,
    MarkdownText,
    PlainText,
)


def create_onboarding_message():

    message = Message(
        blocks=[
            Section(
                text=MarkdownText(
                    text="*Welcome to Early Bird Labs!* :hatching_chick:\nLearn more about what we do and onboard with us."
                )
            ),
            Actions(
                elements=[
                    Button(
                        text=PlainText(text="Start Onboarding"),
                        action_id="start_onboarding",
                    )
                ]
            ),
        ]
    )

    return message.build()


def create_onboarding_modal():
    modal = Modal(
        callback_id="onboarding_modal",
        title=PlainText(text="Start Onboarding"),
        blocks=[
            Input(
                label=PlainText(text="Customer Name"),
                element=PlainTextInput(action_id="customer_name"),
            ),
            Input(
                label=PlainText(text="Company Name"),
                element=PlainTextInput(action_id="company_name"),
            ),
            # Add more Input blocks as needed for your form
        ],
        submit=PlainText(text="Submit"),
        close=PlainText(text="Cancel"),
    )

    return modal.build()
