# banking_agent/context.py

from datetime import datetime, timedelta
import random

class OmnibankContext:
    """
    Contains all the mock data and initial state for the Omnibank banking session,
    aligned with the Rakesh Gowda and Rocky Zayn user journeys.
    """
    # Updated to feature Rakesh Gowda as the primary existing customer.
    # Rocky Zayn will be created dynamically by the verify_identity tool.
    MOCK_CUSTOMER_PROFILES = {
        "cust_rakeshG": {
            "customer_id": "CUST778899",
            "customer_first_name": "Rakesh",
            "customer_last_name": "Gowda",
            "date_of_birth": "1994-07-16",
            "social_security_number": "685685685",
            "identity_verified": False
        },
        # Removed other static profiles to focus on the defined user journeys.
    }

    # Updated to contain accounts relevant to the user journeys.
    MOCK_ACCOUNTS = {
        "ACC778899001": {
            "account_number": "ACC778899001",
            "customer_id": "CUST778899",
            "balance": 25000.50,
            "currency": "USD",
            "status": "active"
        },
        # Added a second account for payment testing purposes.
        "ACC123456789": {
            "account_number": "ACC123456789",
            "customer_id": "CUST_OTHER", # Belongs to another mock user
            "balance": 55000.75,
            "currency": "USD",
            "status": "active"
        },
    }

    # Updated to contain the card for Rakesh Gowda.
    MOCK_DEBIT_CARDS = {
        "CARD5678": {
            "card_id": "CARD5678",
            "customer_id": "CUST778899",
            "account_number": "ACC778899001",
            "last_4_digits": "5678",
            "status": "active",
            "pin_status": "set"
        },
    }

    # Generic data, no changes needed.
    MOCK_FEES = {
        "monthly_service_fee": {
            "name": "Monthly Service Fee",
            "amount": "$5.00",
            "description": "A fee charged each month for account maintenance."
        },
        "atm_withdrawal_fee": {
            "name": "Out-of-network ATM Fee",
            "amount": "$3.00",
            "description": "This fee is charged when you use an ATM outside of the Omnibank network."
        }
    }

    MOCK_LOAN_PRODUCTS = {
        "personal_loan": {
            "name": "Personal Loan",
            "interest_rate": "5.5% APR",
            "max_term_months": 60,
            "description": "A flexible loan for various personal needs."
        },
        "home_loan": {
            "name": "Home Mortgage",
            "interest_rate": "3.8% APR",
            "max_term_months": 360,
            "description": "Finance your dream home."
        },
        "auto_loan": {
            "name": "Auto Loan",
            "interest_rate": "4.2% APR",
            "max_term_months": 72,
            "description": "A loan for a new or used vehicle."
        }
    }

    # Contains the existing loan for Rakesh Gowda.
    MOCK_CUSTOMER_LOANS = {
        "LOAN778899": {
            "loan_id": "LOAN778899",
            "customer_id": "CUST778899",
            "loan_type": "Auto Loan",
            "principal_amount": 20000.00,
            "outstanding_balance": 15250.50,
            "status": "active",
            "interest_rate": "4.2% APR"
        }
    }

    # Contains mock transactions for Rakesh's account.
    MOCK_TRANSACTIONS = {
        "TXN004": {"transaction_id": "TXN004", "account_number": "ACC778899001", "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), "description": "Gas Station", "amount": -55.20},
        "TXN005": {"transaction_id": "TXN005", "account_number": "ACC778899001", "date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), "description": "Utility Bill Payment", "amount": -120.00},
        "TXN007": {"transaction_id": "TXN007", "account_number": "ACC778899001", "date": (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'), "description": "Grocery Store", "amount": -250.75},
    }

    CUSTOMER_BANKING_CONTEXT = {
        "is_banking_session": True,
        "all_customer_profiles": MOCK_CUSTOMER_PROFILES,
        "all_accounts": MOCK_ACCOUNTS,
        "all_debit_cards": MOCK_DEBIT_CARDS,
        "all_fees": MOCK_FEES,
        "all_loan_products": MOCK_LOAN_PRODUCTS,
        "all_customer_loans": MOCK_CUSTOMER_LOANS,
        "all_transactions": MOCK_TRANSACTIONS,
        "current_customer_profile": None,
        "current_account_details": None,
        "current_card_details": None,
        "is_identity_verified": False,
        "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    @staticmethod
    def get_transactions_for_account(state, account_number: str, limit: int = 5):
        transactions = state.get("all_transactions", {}).values()
        account_txns = [t for t in transactions if t.get("account_number") == account_number]
        sorted_txns = sorted(account_txns, key=lambda t: t['date'], reverse=True)
        return sorted_txns[:limit]

    @staticmethod
    def update_balance(state, account_number: str, amount_change: float):
        accounts = state.get("all_accounts", {})
        if account_number in accounts:
            accounts[account_number]["balance"] += amount_change
            new_txn_id = f"TXN-DYN-{random.randint(1000, 9999)}"
            description = f"Payment of ${-amount_change:,.2f}" if amount_change < 0 else f"Deposit of ${amount_change:,.2f}"
            state["all_transactions"][new_txn_id] = {
                "transaction_id": new_txn_id,
                "account_number": account_number,
                "date": datetime.now().strftime('%Y-%m-%d'),
                "description": description,
                "amount": amount_change
            }
            return True
        return False

    @staticmethod
    def get_loan_products_info(state):
        return state.get("all_loan_products", {})

    @staticmethod
    def get_customer_loan(state, customer_id: str):
        loans = state.get("all_customer_loans", {})
        for _, loan in loans.items():
            if loan.get("customer_id") == customer_id:
                return loan.copy()
        return None

    @staticmethod
    def add_new_loan(state, customer_id: str, loan_type: str, amount: float):
        loan_products = state.get("all_loan_products", {})
        product_key = loan_type.replace(" ", "_").lower()
        if product_key not in loan_products:
            return None
        product_details = loan_products[product_key]
        new_loan_id = f"LOAN-DYN-{random.randint(1000, 9999)}"
        new_loan = {
            "loan_id": new_loan_id,
            "customer_id": customer_id,
            "loan_type": product_details["name"],
            "principal_amount": amount,
            "outstanding_balance": amount,
            "status": "approved",
            "interest_rate": product_details["interest_rate"]
        }
        state["all_customer_loans"][new_loan_id] = new_loan
        return new_loan

    @staticmethod
    def find_customer(state, first_name: str, last_name: str, date_of_birth: str, last_4_nin: str):
        profiles = state.get("all_customer_profiles", {})
        for _, profile in profiles.items():
            if (first_name.lower() == profile["customer_first_name"].lower() and
                last_name.lower() == profile["customer_last_name"].lower() and
                date_of_birth == profile["date_of_birth"] and
                last_4_nin == profile["social_security_number"][-4:]):
                return profile.copy()
        return None

    @staticmethod
    def get_account_by_customer_id(state, customer_id: str):
        accounts = state.get("all_accounts", {})
        for _, account in accounts.items():
            if account.get("customer_id") == customer_id:
                return account.copy()
        return None

    @staticmethod
    def update_account_status(state, account_number: str, new_status: str):
        if account_number in state["all_accounts"]:
            state["all_accounts"][account_number]["status"] = new_status
            if new_status == "active" and "lock_reason" in state["all_accounts"][account_number]:
                del state["all_accounts"][account_number]["lock_reason"]
            return True
        return False

    @staticmethod
    def get_card(state, last_4_digits: str, customer_id: str):
        cards = state.get("all_debit_cards", {})
        for _, card in cards.items():
            if (card.get("last_4_digits") == last_4_digits and
                card.get("customer_id") == customer_id):
                return card.copy()
        return None

    @staticmethod
    def get_fee_info(state, fee_type: str):
        normalized_key = fee_type.replace(" ", "_").lower()
        return state.get("all_fees", {}).get(normalized_key)

    @staticmethod
    def update_card_pin_status(state, card_id: str, new_pin_status: str):
        if card_id in state["all_debit_cards"]:
            state["all_debit_cards"][card_id]["pin_status"] = new_pin_status
            return True
        return False
