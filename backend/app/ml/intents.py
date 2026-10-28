UNIFIED_INTENTS = [
    "check_balance", "transaction_history", "spending_summary", "loan_eligibility", "emi_calculation",
    "interest_rates", "loan_products", "card_block", "card_activate", "card_issue", "transfer_money",
    "fees_charges", "atm_branch", "password_pin", "dispute_refund", "human_agent", "faq_general",
]

_B77 = {
    "card_activate": ["activate_my_card"],
    "card_block": ["lost_or_stolen_card", "compromised_card", "lost_or_stolen_phone"],
    "card_issue": ["card_arrival", "card_delivery_estimate", "order_physical_card", "get_physical_card",
                   "getting_spare_card", "card_about_to_expire", "getting_virtual_card",
                   "get_disposable_virtual_card", "card_not_working", "virtual_card_not_working",
                   "contactless_not_working", "card_swallowed", "card_linking"],
    "password_pin": ["change_pin", "pin_blocked", "passcode_forgotten"],
    "atm_branch": ["atm_support"],
    "dispute_refund": ["Refund_not_showing_up", "request_refund", "transaction_charged_twice",
                       "card_payment_not_recognised", "cash_withdrawal_not_recognised",
                       "direct_debit_payment_not_recognised", "wrong_amount_of_cash_received",
                       "reverted_card_payment?", "extra_charge_on_statement",
                       "balance_not_updated_after_bank_transfer",
                       "balance_not_updated_after_cheque_or_cash_deposit"],
    "fees_charges": ["card_payment_fee_charged", "cash_withdrawal_charge", "exchange_charge",
                     "transfer_fee_charged", "top_up_by_bank_transfer_charge", "top_up_by_card_charge"],
    "transfer_money": ["cancel_transfer", "failed_transfer", "declined_transfer", "pending_transfer",
                       "transfer_not_received_by_recipient", "transfer_timing", "transfer_into_account",
                       "beneficiary_not_allowed", "receiving_money"],
}
BANKING77_MAP: dict[str, str] = {src: tgt for tgt, srcs in _B77.items() for src in srcs}

_BITEXT = {
    "card_activate": ["activate_card", "activate_card_international_usage"],
    "loan_products": ["apply_for_loan", "apply_for_mortgage"],
    "card_block": ["block_card", "cancel_card"],
    "faq_general": ["cancel_loan", "cancel_mortgage", "close_account", "create_account"],
    "fees_charges": ["check_card_annual_fee", "check_fees"],
    "check_balance": ["check_current_balance_on_card"],
    "emi_calculation": ["check_loan_payments", "check_mortgage_payments"],
    "transaction_history": ["check_recent_transactions"],
    "human_agent": ["customer_service", "human_agent"],
    "dispute_refund": ["dispute_ATM_withdrawal"],
    "atm_branch": ["find_ATM", "find_branch"],
    "password_pin": ["get_password", "set_up_password"],
    "transfer_money": ["make_transfer", "cancel_transfer"],
    "card_issue": ["recover_swallowed_card"],
}
BITEXT_MAP: dict[str, str] = {src: tgt for tgt, srcs in _BITEXT.items() for src in srcs}


def map_banking77(label: str) -> str:
    return BANKING77_MAP.get(label, "faq_general")


def map_bitext(label: str) -> str:
    return BITEXT_MAP.get(label, "faq_general")
