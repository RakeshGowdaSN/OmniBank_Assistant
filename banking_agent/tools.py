# banking_agent/tools.py

import logging
import random
import string
from contextvars import ContextVar

# This is the single, essential context variable for enabling stateful memory.
session_context = ContextVar('session_object', default=None)

# The context import is now relative to this file's location.
from .context import OmnibankContext

logger = logging.getLogger(__name__)

def _get_and_init_state():
    """
    Gets the session from contextvars and initializes banking state if not present.
    """
    session = session_context.get()
    if not session:
        raise Exception("Fatal Error: Could not find session in context. State management is broken.")

    if not session.state.get("is_banking_session"):
        logger.info(f"Initializing banking context for session: {session.id}")
        session.state.update(OmnibankContext.CUSTOMER_BANKING_CONTEXT)

    return session.state

def _generate_mock_pin() -> str:
    """Generates a random 4-digit PIN."""
    return ''.join(random.choices(string.digits, k=4))

# --- Conversational Tools ---
def greeting() -> dict:
    """A static default greeting sent to the user to start the conversation."""
    return {"greeting": "Welcome to Omnibank. You're speaking with Zenith, your personal virtual assistant. How can I help you make your banking simpler today?"}


def affirmative() -> dict:
    """Indicates a verbal affirmative from the user was provided to the agent's question."""
    return {"status": "success", "message": "User confirmed."}

def transfer_to_human() -> dict:
    """Signals that the conversation needs to be transferred to a human agent."""
    return {"status": "transfer", "message": "I am now transferring you to a human representative. Please hold."}

# --- Stateful Banking Tools ---
def verify_identity(first_name: str, last_name: str, date_of_birth: str, last_4_nin: str) -> dict:
    state = _get_and_init_state()
    customer_profile = OmnibankContext.find_customer(state, first_name, last_name, date_of_birth, last_4_nin)
    if customer_profile:
        state["is_identity_verified"] = True
        state["current_customer_profile"] = customer_profile
        state["current_account_details"] = OmnibankContext.get_account_by_customer_id(state, customer_profile['customer_id'])
        return {
            "status": "verified",
            "message": f"Thank you, {customer_profile.get('customer_first_name')}. Your identity has been successfully verified."
        }
    else:
        new_profile = {"customer_id": f"DYN-{last_4_nin}", "customer_first_name": first_name, "customer_last_name": last_name, "date_of_birth": date_of_birth, "social_security_number": f"xxxx{last_4_nin}", "identity_verified": True}
        new_account_number = f"ACC-DYN-{last_4_nin}"
        new_account = {"account_number": new_account_number, "customer_id": new_profile["customer_id"], "balance": 7500.00, "currency": "USD", "status": "active"}
        state["all_accounts"][new_account_number] = new_account
        state["is_identity_verified"] = True
        state["current_customer_profile"] = new_profile
        state["current_account_details"] = new_account
        return {
            "status": "verified",
            "message": f"Thank you, {first_name}. Your identity has been successfully verified."
        }

def check_account_status() -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    account = state.get("current_account_details", {})
    if not account:
        return {"status": "not_found", "message": "I couldn't find an account associated with your profile."}

    status = account.get("status", "unknown")
    last4 = account.get("account_number", "----")[-4:]
    if status == "locked":
        reason = account.get("lock_reason", "an unspecified reason")
        return {
            "status": "locked",
            "account_number": account['account_number'],
            "message": f"Your account ending in {last4} is currently locked due to {reason}."
        }
    return {"status": "active", "message": f"Your account ending in {last4} is currently active."}

def unlock_account(account_number: str) -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    if OmnibankContext.update_account_status(state, account_number, "active"):
        return {"status": "success", "message": f"Account ending in {account_number[-4:]} has been successfully unlocked."}
    
    return {"status": "error", "message": "An internal error occurred."}

def get_account_balance() -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    account = state.get("current_account_details", {})
    if not account:
        return {"status": "not_found", "message": "I couldn't find an account for your profile."}

    balance = account.get("balance", 0)
    last4 = account.get("account_number", "----")[-4:]
    return {"status": "success", "message": f"Your current balance for the account ending in {last4} is ${balance:,.2f}."}

def get_fee_details(fee_type: str) -> dict:
    state = _get_and_init_state()
    fee_info = OmnibankContext.get_fee_info(state, fee_type)
    if fee_info:
        return {
            "status": "success",
            "details": f"Fee Name: {fee_info['name']}, Amount: {fee_info['amount']}, Description: {fee_info['description']}"
        }
    return {"status": "not_found", "message": f"I couldn't find information about '{fee_type}'."}

def get_card_details(last_4_digits: str) -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    customer_id = state.get("current_customer_profile", {}).get("customer_id")
    card = OmnibankContext.get_card(state, last_4_digits=last_4_digits, customer_id=customer_id)
    if card:
        state["current_card_details"] = card
        return {
            "status": "success",
            "card_id": card["card_id"],
            "preview": f"Card ending in {card['last_4_digits']}, Status: {card['status']}"
        }
    return {"status": "not_found", "message": f"I couldn't find a card ending in {last_4_digits}."}

def reset_card_pin(card_id: str) -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    card = state.get("current_card_details", {})
    if not card or card.get("card_id") != card_id:
        return {"status": "mismatch", "message": "There was a mismatch. Please start the card lookup process again."}

    if card.get("status") != "active":
        return {"status": "card_inactive", "message": "This card is not active."}

    new_pin = _generate_mock_pin()
    OmnibankContext.update_card_pin_status(state, card_id, "set")
    return {"status": "success", "message": f"Your new temporary PIN is {new_pin}. Please change this at an ATM."}

def get_loan_products() -> dict:
    state = _get_and_init_state()
    products = OmnibankContext.get_loan_products_info(state)
    product_list = [f"{v['name']} (Rate: {v['interest_rate']})" for k, v in products.items()]
    return {"status": "success", "products": ", ".join(product_list)}

def get_loan_details() -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    customer_id = state.get("current_customer_profile", {}).get("customer_id")
    loan = OmnibankContext.get_customer_loan(state, customer_id)
    if loan:
        return {
            "status": "success",
            "details": f"You have a {loan['loan_type']} with an outstanding balance of ${loan['outstanding_balance']:,.2f}. The interest rate is {loan['interest_rate']}."
        }
    return {"status": "not_found", "message": "I couldn't find any existing loans for your profile."}

def apply_for_loan(loan_type: str, amount: float) -> dict:
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required first."}

    customer_id = state.get("current_customer_profile", {}).get("customer_id")
    if OmnibankContext.get_customer_loan(state, customer_id):
        return {"status": "ineligible", "message": "Our records show you already have an active loan."}

    new_loan = OmnibankContext.add_new_loan(state, customer_id, loan_type, amount)
    if not new_loan:
        return {"status": "error", "message": f"I'm sorry, we don't offer a '{loan_type}' at the moment."}

    return {
        "status": "success",
        "message": f"Congratulations! Your application for a {loan_type} of ${amount:,.2f} has been approved. Your Loan ID is {new_loan['loan_id']}."
    }

def list_recent_transactions() -> dict:
    """Lists the most recent transactions for the customer's primary account. Requires identity verification."""
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required to view transactions."}
    
    account = state.get("current_account_details", {})
    if not account:
        return {"status": "not_found", "message": "I couldn't find an account for your profile."}
        
    transactions = OmnibankContext.get_transactions_for_account(state, account['account_number'])
    if not transactions:
        return {"status": "success", "details": "You have no recent transactions."}
    
    # Format the transactions into a readable string
    details_list = [f"Date: {t['date']}, Description: {t['description']}, Amount: ${t['amount']:,.2f}" for t in transactions]
    return {"status": "success", "details": "\n".join(details_list)}


def make_payment(recipient_account_number: str, amount: float) -> dict:
    """Makes a payment from the customer's primary account to another account. Requires identity verification."""
    state = _get_and_init_state()
    if not state.get("is_identity_verified"):
        return {"status": "denied", "message": "Identity verification is required to make a payment."}
        
    sender_account = state.get("current_account_details", {})
    if not sender_account:
        return {"status": "not_found", "message": "I couldn't find your account to send the payment from."}

    # Basic validation
    if amount <= 0:
        return {"status": "invalid_amount", "message": "Payment amount must be positive."}
    if sender_account['balance'] < amount:
        return {"status": "insufficient_funds", "message": "You do not have sufficient funds to make this payment."}
    if recipient_account_number not in state.get("all_accounts", {}):
         return {"status": "recipient_not_found", "message": "The recipient account number does not seem to be valid."}

    # Simulate the transaction
    OmnibankContext.update_balance(state, sender_account['account_number'], -amount)
    OmnibankContext.update_balance(state, recipient_account_number, amount)

    return {"status": "success", "message": f"Payment of ${amount:,.2f} to account {recipient_account_number} was successful."}
