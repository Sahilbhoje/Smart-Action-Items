

"""
test_notes.py - Unified test runner for Smart Action Items API.
Runs all 35 test cases one by one. Invalid inputs are flagged inline.
"""

import requests

API_URL = "http://localhost:8000/extract-actions"

# All test cases: (notes, is_valid)
all_test_cases = [
    # ✅ Valid cases
    ("Raj will fix the login bug by Friday. Sarah needs to deploy the hotfix by Monday.", True),
    ("Someone needs to update the README documentation before the next sprint.", True),
    ("John will review the open pull requests soon.", True),
    ("Priya is responsible for writing unit tests, updating the API docs, and setting up CI/CD.", True),
    ("- Fix navbar alignment bug - Amit\n- Write migration script - due Thursday\n- Update environment variables\n- Schedule client demo - Neha - next Tuesday", True),
    ("In today's standup Vikram is going to handle the payment gateway integration before sprint ends on the 30th. Nobody has picked up the logging task yet.", True),
    ("todo: deploy hotfix (urgent!!), ravi - check server logs tmrw, standup 10am fri", True),
    ("We had a general discussion about company culture and team morale. Nothing specific was decided.", True),
    ("Raj and Priya will co-own the dashboard redesign. Deadline is end of month.", True),
    ("Meeting notes 14th June:\n- Ankit: database backup script by Wednesday\n- Sneha will handle client onboarding emails\n\nKaran volunteered to look into search page performance but no deadline set.", True),
    ("The production server is down. DevOps team needs to fix it ASAP. Rohan is on it.", True),
    ("Submit the quarterly report by 30/06. Meena owns this.", True),
    ("Need to migrate the old database to PostgreSQL. Should be done by end of Q3.", True),
    ("jhon shuld reveiw the desgn mockups by next wendsday. sara wil update the stying", True),
    ("Product sync - 3rd July\nDev team:\n- Rahul to finish search feature by July 10\n- Backend API optimisation - Suresh - July 15\nDesign:\n- Finalize mobile screens - Kavita - July 8\nQA:\n- Set up automated testing - Deepak - before release\n- Review test cases - Asha - ASAP", True),
    ("Arjun: database indexing. Meera: frontend performance. Siddharth: API rate limiting.", True),
    ("I was thinking maybe someone should look into the memory leak issue? And the auth token expiry bug should also be fixed at some point.", True),
    ("Deploy by 5pm today. Raj.", True),
    ("Great meeting everyone! By the way, Nisha will prepare the investor deck by Thursday.", True),
    ("Bhai, Rohit ko Monday tak login page fix karni hai. Aur staging deploy karo jaldi.", True),
    ("I had a call with Sahil and asked him to look into the PyTest issue. Next, I will connect with Aaysha and ask her to work on the PyPath issue. She has assured me that she will come back with the timeline by EOD.", True),

    # ❌ Invalid cases
    ("", False),
    ("     ", False),
    ("@@### !!! $$$ ???", False),
    ("1234567890", False),
    ("Raj.", False),
    ("blah blah blah blah blah blah blah blah", False),
    ("x" * 5000, False),
    ("By Friday.", False),
    ("<script>alert('xss')</script>", False),
    ("🔥🚀💀❌✅🎯", False),
    
]


def run_all_tests():
    print("=" * 60)
    print("Smart Action Items - Test Runner")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, (notes, is_valid) in enumerate(all_test_cases, 1):
        print(f"\n--- Test {i} ---")
        print(f"Input: {notes.strip()[:80]}{'...' if len(notes.strip()) > 80 else ''}")

        try:
            response = requests.post(API_URL, json={"notes": notes}, timeout=30)
            status = response.status_code

            if is_valid:
                # ✅ Valid input — expect 200 with actions
                if status == 200:
                    actions = response.json().get("actions", [])
                    print(f"✅ Status: 200 | Actions found: {len(actions)}")
                    for action in actions:
                        print(f"   → Task: {action['task']}")
                        print(f"     Owner: {action['owner']} | Deadline: {action['deadline']}")
                    passed += 1
                else:
                    print(f"✗  Expected 200 but got {status} | Error: {response.text}")
                    failed += 1

            else:
                # ❌ Invalid input — expect 400 or 200 with empty []
                if status == 400:
                    print(f"❌ Invalid Input | Correctly rejected with 400: {response.json()['detail']}")
                    passed += 1
                elif status == 200:
                    actions = response.json().get("actions", [])
                    if not actions:
                        print(f"❌ Invalid Input | Returned empty [] — handled gracefully")
                        passed += 1
                    else:
                        print(f"❌ Invalid Input | ⚠️ Hallucinated {len(actions)} fake action(s):")
                        for a in actions:
                            print(f"   → Task: {a['task']} | Owner: {a['owner']} | Deadline: {a['deadline']}")
                        failed += 1
                else:
                    print(f"❌ Invalid Input | Unexpected status {status}: {response.text[:100]}")
                    failed += 1

        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to API. Is the server running? (python -m uvicorn main:app --reload)")
            return
        except Exception as e:
            print(f"❌ Exception: {e}")
            failed += 1

    total = len(all_test_cases)
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed | {failed} failed | {total} total")
    print(f"Valid tests:   20  |  Invalid tests: 15")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()