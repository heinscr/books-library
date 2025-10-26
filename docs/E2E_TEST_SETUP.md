# E2E Test Setup - Current Status

## What's Been Set Up

✅ **Infrastructure Complete:**
- Playwright installed (v1.55.0)
- Chromium browser installed
- Test framework configured
- 43+ end-to-end tests written covering:
  - Authentication flows (11 tests)
  - Book grid display and filtering (13 tests)
  - Book operations and accessibility (19 tests)

✅ **Configuration:**
- conftest.py with authentication fixtures
- Helper script (run-e2e-tests.sh) for easy test execution
- Comprehensive documentation

## What's Needed to Run Tests

### 1. Set Test Credentials

```bash
export TEST_USER_EMAIL='your-email@example.com'
export TEST_USER_PASSWORD='your-password'
```

Or create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your credentials
```

### 2. Configure Frontend URL

The tests run against the URL configured in `tests/e2e/conftest.py` (BASE_URL fixture).
Update this to point to your deployment:

```python
@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "https://your-frontend-url.com")
```

Before running tests, verify the URL loads in your browser and shows the login form.

**Note**: If the site loads slowly or has issues, you may need to:
- Increase timeouts in the tests
- Check your frontend deployment configuration
- Ensure the frontend is accessible from your test environment

### 3. Run Tests

```bash
# Basic test (no auth required)
PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::TestBookGrid::test_page_loads -v

# All tests (requires TEST_USER_EMAIL and TEST_USER_PASSWORD)
./run-e2e-tests.sh

# With visible browser for debugging
./run-e2e-tests.sh --headed
```

## Troubleshooting

If tests are timing out waiting for the login form:

1. **Frontend Not Accessible**
   - Verify your frontend URL loads in a browser
   - Check if the login form appears
   - Ensure network access from test environment

2. **Slow Page Load**
   - Increase timeout from 10000ms to 30000ms in tests
   - Check network performance
   - Consider running tests closer to your deployment

3. **Wrong URL**
   - Double-check the BASE_URL in conftest.py
   - Try setting BASE_URL environment variable for testing

## Quick Debug Steps

1. **Test the URL manually:**
   ```bash
   curl -I https://your-frontend-url.com
   ```

2. **Run test with visible browser:**
   ```bash
   PYTHONPATH=. pipenv run pytest tests/e2e/test_book_grid.py::TestBookGrid::test_page_loads -v --headed --slowmo 1000
   ```

3. **Override URL for testing:**
   ```bash
   BASE_URL=https://your-test-url.com ./run-e2e-tests.sh
   ```

## Test Files Created

1. **tests/e2e/conftest.py** - Test configuration and fixtures
2. **tests/e2e/test_authentication.py** - Login/logout tests (11 tests)
3. **tests/e2e/test_book_grid.py** - Book display tests (13 tests)
4. **tests/e2e/test_book_operations.py** - Book editing tests (19 tests)
5. **run-e2e-tests.sh** - Helper script
6. **tests/e2e/README.md** - Comprehensive documentation

## Once Tests Are Running

After you resolve the URL/loading issue and set credentials, you'll be able to run:

```bash
# All tests
./run-e2e-tests.sh

# Specific test file
./run-e2e-tests.sh test_authentication.py

# With debugging
./run-e2e-tests.sh --debug

# Different browser
./run-e2e-tests.sh --firefox
```

The tests will automatically:
- Log in with your credentials
- Test all critical user flows
- Clean up after themselves (restore original values)
- Report any failures

## Next Steps

1. Verify which CloudFront URL is correct
2. Set TEST_USER_EMAIL and TEST_USER_PASSWORD environment variables
3. Run a single test to verify it works
4. Run full test suite
5. Optionally add to CI/CD pipeline
