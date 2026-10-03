"""Template knowledge used ONLY in offline mode (no LLM configured) and as a safety net.

Each pack = list of (requirement_text, [case, ...]).
case = (scenario, steps "a > b > c", test_data, expected_result, priority, test_type, polarity)
"""
V, N, F, B, S, E = "Validation", "Negative", "Functional", "Boundary", "Security", "Error Handling"

PACKS: dict[str, list] = {
    "Authentication": [
        ("Email field is mandatory and must have a valid email format", [
            ("Login with empty email", "Open login page > Leave email empty > Enter valid password > Click Login",
             "email: (empty); password: Valid@123", "A message says the email is required; login is blocked", "Medium", V, "Negative"),
            ("Login with invalid email format", "Open login page > Enter 'user@@mail' as email > Enter valid password > Click Login",
             "email: user@@mail; password: Valid@123", "An invalid email format message is displayed", "Medium", V, "Negative")]),
        ("Password field is mandatory", [
            ("Login with empty password", "Open login page > Enter valid email > Leave password empty > Click Login",
             "email: user@example.com; password: (empty)", "A message says the password is required; login is blocked", "Medium", V, "Negative")]),
        ("Valid credentials grant access to the account dashboard", [
            ("Login with valid credentials", "Open login page > Enter registered email > Enter correct password > Click Login",
             "email: user@example.com; password: Valid@123", "User is logged in and the dashboard is displayed", "High", F, "Positive"),
            ("Password is masked while typing", "Open login page > Type a password in the password field",
             "password: Valid@123", "Characters are masked and not shown in plain text", "Low", "Usability", "Positive")]),
        ("Invalid credentials are rejected with an error message", [
            ("Login with incorrect password", "Open login page > Enter registered email > Enter wrong password > Click Login",
             "email: user@example.com; password: Wrong@999", "An invalid credentials error is shown; user is not logged in", "High", E, "Negative"),
            ("Login with unregistered email", "Open login page > Enter unregistered email > Enter any password > Click Login",
             "email: nobody@example.com; password: Valid@123", "An invalid credentials error is shown; no account details are leaked", "High", E, "Negative")]),
        ("Repeated failed login attempts and injection attempts are handled securely", [
            ("Account lockout after repeated failed logins", "Open login page > Submit wrong password five times in a row > Submit the correct password",
             "attempts: 5; password: Wrong@999", "The account is temporarily locked and a lockout message is displayed", "High", S, "Negative"),
            ("SQL injection attempt in email field", "Open login page > Enter \"' OR '1'='1\" as email > Enter any password > Click Login",
             "email: ' OR '1'='1", "Input is rejected or sanitised; no access is granted", "High", S, "Negative")]),
    ],
    "Payment": [
        ("Valid card details complete the payment and a confirmation is shown", [
            ("Pay with a valid credit card", "Add item to cart > Go to checkout > Enter valid card details > Click Pay",
             "card: 4111 1111 1111 1111; expiry: 12/30; cvv: 123", "Payment succeeds and an order confirmation is displayed", "High", F, "Positive"),
            ("Payment receipt is generated", "Complete a successful payment > Open the order confirmation page",
             "order: any paid order", "A receipt with amount and transaction id is available", "Medium", F, "Positive")]),
        ("Invalid or expired cards are rejected", [
            ("Pay with an expired card", "Go to checkout > Enter card with past expiry date > Click Pay",
             "expiry: 01/20", "An expired card error is shown and no charge is made", "High", V, "Negative"),
            ("Pay with an invalid card number", "Go to checkout > Enter card number failing the Luhn check > Click Pay",
             "card: 1234 5678 9012 3456", "An invalid card number message is displayed", "High", V, "Negative")]),
        ("Insufficient funds and gateway failures are handled gracefully", [
            ("Payment declined for insufficient funds", "Go to checkout > Enter card with insufficient balance > Click Pay",
             "card: test declined card", "A declined message is shown; order stays unpaid; user can retry", "High", E, "Negative"),
            ("Payment gateway timeout", "Go to checkout > Enter valid card > Simulate gateway timeout > Click Pay",
             "gateway: timeout", "A friendly retry message appears and the user is not charged twice", "Medium", E, "Negative")]),
        ("Mandatory card fields are validated and card data is protected", [
            ("Submit payment with empty mandatory fields", "Go to checkout > Leave card number and CVV empty > Click Pay",
             "card fields: (empty)", "Validation messages are shown for each mandatory field", "Medium", V, "Negative"),
            ("CVV is masked", "Go to checkout > Type CVV in the CVV field", "cvv: 123", "CVV characters are masked", "Medium", S, "Positive")]),
        ("Amount charged must match the order total and duplicate submissions must not double charge", [
            ("Charged amount equals order total", "Add items to cart > Note order total > Complete payment > Check the transaction amount",
             "cart total: 1,499.00", "The charged amount equals the displayed order total", "High", F, "Positive"),
            ("Double click on Pay button", "Go to checkout > Enter valid card > Double-click Pay",
             "action: double click", "Only one transaction is created", "High", "Error Handling", "Negative")]),
    ],
    "Registration": [
        ("All mandatory registration fields must be provided", [
            ("Register with all fields empty", "Open registration page > Leave all fields empty > Click Register",
             "all fields: (empty)", "Mandatory field messages are shown; no account is created", "High", V, "Negative"),
            ("Register leaving the email empty", "Open registration page > Fill every field except email > Click Register",
             "email: (empty)", "An email is required message is displayed", "Medium", V, "Negative")]),
        ("Email must be valid and unique", [
            ("Register with an already registered email", "Open registration page > Enter an existing email > Fill other fields > Click Register",
             "email: existing@example.com", "An email already exists message is displayed", "High", V, "Negative"),
            ("Register with invalid email format", "Open registration page > Enter 'abc.com' as email > Click Register",
             "email: abc.com", "An invalid email format message is displayed", "Medium", V, "Negative")]),
        ("Password must meet complexity and length rules", [
            ("Register with a weak password", "Open registration page > Enter a weak password > Click Register",
             "password: 12345", "Password rules are displayed and registration is blocked", "High", V, "Negative"),
            ("Password minimum length boundary", "Open registration page > Enter 7-character then 8-character password > Click Register",
             "password: Abcd@12 and Abcd@123", "7 characters is rejected, 8 characters is accepted", "Medium", B, "Positive")]),
        ("Successful registration creates the account and sends a verification email", [
            ("Register with valid details", "Open registration page > Fill all fields with valid data > Click Register",
             "name: Asha; email: new@example.com; password: Abcd@123", "Account is created and a success message is displayed", "High", F, "Positive"),
            ("Verification email is sent", "Register with valid details > Open the inbox",
             "email: new@example.com", "A verification email with a working link is received", "Medium", F, "Positive")]),
        ("Password and confirm password must match", [
            ("Mismatching confirm password", "Open registration page > Enter password > Enter a different confirm password > Click Register",
             "password: Abcd@123; confirm: Abcd@124", "A passwords do not match message is displayed", "Medium", V, "Negative")]),
    ],
    "Search": [
        ("Search returns results matching the entered keyword", [
            ("Search with a valid keyword", "Open the application > Enter a valid keyword in the search box > Click Search",
             "keyword: laptop", "Results matching the keyword are listed", "High", F, "Positive"),
            ("Search is case insensitive", "Search for 'LAPTOP' > Search for 'laptop' > Compare results",
             "keyword: LAPTOP / laptop", "Both searches return the same results", "Medium", F, "Positive")]),
        ("Empty search input is handled", [
            ("Search with empty keyword", "Open the application > Leave the search box empty > Click Search",
             "keyword: (empty)", "A prompt to enter a keyword is shown or default results appear without errors", "Medium", V, "Negative")]),
        ("A clear message is shown when no results are found", [
            ("Search with a keyword that has no match", "Open the application > Enter a nonsense keyword > Click Search",
             "keyword: zzzxqv", "A no results found message is displayed", "Medium", E, "Negative")]),
        ("Special characters and very long input are handled safely", [
            ("Search with special characters", "Open the application > Enter special characters in the search box > Click Search",
             "keyword: <script>@#$%", "Input is sanitised; no script runs; no server error", "High", S, "Negative"),
            ("Search with a very long keyword", "Open the application > Paste a 300-character keyword > Click Search",
             "keyword: 300 characters", "The input is truncated or rejected gracefully", "Low", B, "Negative")]),
        ("Search results can be filtered and sorted", [
            ("Filter search results", "Search for a keyword > Apply a price filter", "filter: price 500-1000",
             "Only results within the filter are shown", "Medium", F, "Positive"),
            ("Sort search results", "Search for a keyword > Sort by price low to high", "sort: price ascending",
             "Results are ordered by ascending price", "Medium", F, "Positive")]),
    ],
    "Shopping Cart": [
        ("User can add items to the shopping cart", [
            ("Add a single item to the cart", "Open a product page > Click Add to Cart > Open the cart",
             "item: any in-stock product", "The item appears in the cart with correct price and quantity 1", "High", F, "Positive"),
            ("Add multiple different items", "Add item A to the cart > Add item B to the cart > Open the cart",
             "items: A, B", "Both items are listed and the count is 2", "Medium", F, "Positive")]),
        ("Item quantity can be updated within stock limits", [
            ("Increase item quantity", "Open the cart > Increase quantity to 3", "quantity: 3",
             "Quantity and line total update correctly", "Medium", F, "Positive"),
            ("Quantity boundary values", "Open the cart > Set quantity to 0 > Set quantity above available stock",
             "quantity: 0 and stock+1", "Zero removes or is rejected; above stock shows a stock limit message", "High", B, "Negative")]),
        ("Items can be removed from the cart", [
            ("Remove an item from the cart", "Open the cart > Click Remove on an item", "item: any cart item",
             "The item disappears and the total is recalculated", "Medium", F, "Positive"),
            ("Empty cart message", "Remove all items from the cart", "cart: empty",
             "An empty cart message is displayed and checkout is disabled", "Low", F, "Positive")]),
        ("Cart total including discounts and taxes is calculated correctly", [
            ("Cart total with multiple items", "Add two items with different prices > Open the cart > Check the total",
             "prices: 100 and 250; tax: 10%", "Total equals (100 + 250) plus tax", "High", F, "Positive"),
            ("Apply an invalid coupon", "Open the cart > Enter an invalid coupon code > Click Apply",
             "coupon: INVALID1", "An invalid coupon message is shown; total is unchanged", "Medium", V, "Negative")]),
        ("Cart persists across sessions", [
            ("Cart persists after logout and login", "Add an item > Log out > Log in again > Open the cart",
             "item: any product", "The cart still contains the item", "Medium", F, "Positive")]),
    ],
    "Profile": [
        ("User can view profile details", [
            ("View profile page", "Log in > Open the profile page", "user: existing user",
             "Name, email and phone are displayed correctly", "Medium", F, "Positive")]),
        ("User can update profile information and changes are saved", [
            ("Update name and phone number", "Open profile > Edit name and phone > Click Save",
             "name: Ravi K; phone: 9876543210", "A success message appears and new values are shown", "High", F, "Positive"),
            ("Profile changes persist after re-login", "Update the profile > Log out > Log in > Open profile",
             "name: Ravi K", "The updated values are still present", "Medium", F, "Positive")]),
        ("Mandatory profile fields cannot be blank and formats are validated", [
            ("Save profile with blank name", "Open profile > Clear the name field > Click Save", "name: (empty)",
             "A name is required message is displayed and nothing is saved", "Medium", V, "Negative"),
            ("Save profile with invalid phone number", "Open profile > Enter letters in phone > Click Save",
             "phone: abc123", "An invalid phone number message is displayed", "Medium", V, "Negative")]),
        ("Profile picture accepts only valid file types and sizes", [
            ("Upload a valid profile picture", "Open profile > Upload a 1 MB PNG > Click Save", "file: photo.png (1 MB)",
             "The picture is uploaded and displayed", "Medium", F, "Positive"),
            ("Upload an unsupported or oversized file", "Open profile > Upload a 5 MB PDF > Click Save", "file: doc.pdf (5 MB)",
             "An unsupported type or size limit message is displayed", "Medium", B, "Negative")]),
    ],
    "Notification": [
        ("A notification is triggered by the relevant event", [
            ("Notification on triggering event", "Log in > Perform the event that triggers a notification > Check notifications",
             "event: order shipped", "A notification for the event is received", "High", F, "Positive")]),
        ("User can enable or disable notifications", [
            ("Disable notifications", "Open notification settings > Turn notifications off > Trigger an event",
             "setting: off", "No notification is delivered", "High", F, "Negative"),
            ("Enable notifications again", "Open notification settings > Turn notifications on > Trigger an event",
             "setting: on", "The notification is delivered", "Medium", F, "Positive")]),
        ("Notification content is accurate", [
            ("Verify notification content", "Trigger a notification > Open it", "event: order shipped",
             "Title, message and timestamp match the event", "Medium", F, "Positive")]),
        ("Notifications are delivered on the configured channels", [
            ("Email channel delivery", "Select email as the channel > Trigger an event > Open the inbox", "channel: email",
             "An email notification arrives within the expected time", "Medium", F, "Positive"),
            ("Push channel delivery", "Select push as the channel > Trigger an event", "channel: push",
             "A push notification is displayed on the device", "Medium", F, "Positive")]),
        ("Notifications can be marked as read without duplicates", [
            ("Mark a notification as read", "Open notification centre > Mark one as read", "notification: unread",
             "It is shown as read and the unread count decreases", "Low", F, "Positive"),
            ("No duplicate notification for one event", "Trigger one event > Check notifications", "event: single",
             "Exactly one notification exists for the event", "Medium", E, "Negative")]),
    ],
    "Data Management": [
        ("User can create a new record with valid data", [
            ("Create a record with valid data", "Open the create form > Fill all fields with valid data > Click Save",
             "valid sample record", "The record is saved and appears in the list", "High", F, "Positive")]),
        ("Mandatory fields are validated on create and update", [
            ("Create a record with missing mandatory fields", "Open the create form > Leave mandatory fields empty > Click Save",
             "mandatory fields: (empty)", "Validation messages are shown; the record is not saved", "High", V, "Negative")]),
        ("User can edit an existing record", [
            ("Edit an existing record", "Open a record > Click Edit > Change a field > Click Save", "field: changed value",
             "The updated value is saved and shown", "High", F, "Positive")]),
        ("A record can be deleted only after confirmation", [
            ("Delete a record after confirming", "Select a record > Click Delete > Confirm", "record: any",
             "The record is removed from the list", "High", F, "Positive"),
            ("Cancel the delete confirmation", "Select a record > Click Delete > Click Cancel", "record: any",
             "The record is not deleted", "Medium", F, "Negative")]),
        ("Invalid data types and maximum field lengths are handled", [
            ("Enter text in a numeric field", "Open the create form > Enter letters in a numeric field > Click Save",
             "age: abc", "An invalid value message is displayed", "Medium", V, "Negative"),
            ("Maximum length boundary", "Open the create form > Enter max-length then max+1 characters > Click Save",
             "name: 50 and 51 characters", "Max length is accepted; max+1 is rejected", "Medium", B, "Negative")]),
    ],
    "General": [
        ("The main flow works with valid input", [
            ("Main flow with valid input", "Open the application > Perform the main action with valid data > Submit",
             "valid sample data", "The action completes successfully and confirmation is shown", "High", F, "Positive")]),
        ("Invalid input is rejected with a clear error message", [
            ("Main flow with invalid input", "Open the application > Enter invalid data > Submit", "invalid sample data",
             "A clear error message is displayed and nothing is saved", "High", V, "Negative")]),
        ("Mandatory inputs are validated", [
            ("Submit with mandatory inputs empty", "Open the application > Leave mandatory inputs empty > Submit",
             "inputs: (empty)", "Mandatory field messages are displayed", "Medium", V, "Negative")]),
        ("Unauthorised users cannot access the feature", [
            ("Access the feature without logging in", "Open the feature URL directly without logging in", "session: none",
             "The user is redirected to login or sees an access denied message", "High", S, "Negative")]),
    ],
}
