"""Compliance constants"""

# computed result states
RESULT_SUCCESS = "SUCCESS"
RESULT_MANUALLY_APPROVED = "MANUALLY_APPROVED"
RESULT_DENIED = "DENIED"
RESULT_TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
RESULT_UNKNOWN = "UNKNOWN"
RESULT_CHOICES = (
    RESULT_SUCCESS,
    RESULT_MANUALLY_APPROVED,
    RESULT_DENIED,
    RESULT_TEMPORARY_FAILURE,
    RESULT_UNKNOWN,
)

# REASON CODES

# "SUCCESS"
REASON_CODE_SUCCESS = 100

# INPUT ERRORS
REASON_CODE_MISSING_FIELDS = 101
REASON_CODE_INVALID_FIELDS = 102

# BACKEND FAILURES
REASON_CODE_GENERAL_FAILURE = 150
REASON_CODE_SERVER_TIMEOUT = 151
REASON_CODE_SERVICE_TIMEOUT = 152

# CONFIGURATION FAILURES
REASON_CODE_MERCHANT_CONFIG_ERROR = 234

# EXPORTS DENIED
REASON_CODE_EMBARGO_CUSTOMER = 700
REASON_CODE_EMBARGO_COUNTRY = 701
REASON_CODE_EMBARGO_COUNTRY_EMAIL = 702
REASON_CODE_EMBARGO_COUNTRY_BY_IP = 703

# REASON CODE SETS
INVALID_REQUEST_REASON_CODES = [REASON_CODE_MISSING_FIELDS, REASON_CODE_INVALID_FIELDS]
CYBERSOURCE_BACKEND_FAILURE_REASON_CODES = [
    REASON_CODE_GENERAL_FAILURE,
    REASON_CODE_SERVER_TIMEOUT,
    REASON_CODE_SERVICE_TIMEOUT,
]
CYBERSOURCE_CONFIG_ERROR_REASON_CODES = [REASON_CODE_MERCHANT_CONFIG_ERROR]

TEMPORARY_FAILURE_REASON_CODES = (
    INVALID_REQUEST_REASON_CODES
    + CYBERSOURCE_BACKEND_FAILURE_REASON_CODES
    + CYBERSOURCE_CONFIG_ERROR_REASON_CODES
)

EXPORTS_BLOCKED_REASON_CODES = [
    REASON_CODE_EMBARGO_CUSTOMER,
    REASON_CODE_EMBARGO_COUNTRY,
    REASON_CODE_EMBARGO_COUNTRY_EMAIL,
    REASON_CODE_EMBARGO_COUNTRY_BY_IP,
]
