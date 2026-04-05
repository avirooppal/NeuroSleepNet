# NeuroSleepNet Runbook

Here is your complete guide to running the full Local Stack (Backend APIs + Metric Dashboards) and executing the test suites.

---

## 1. Start the Backend API Server

The backend runs on FastAPI and exposes all the V2 endpoints. It needs to run in the background for the dashboards and test scripts to work.

**Command:**
```bash
# Ensure you are in the project root
cd /home/avi/aviroop/NeuroSleepNet

# Start the uvicorn server using uv
uv run uvicorn api.main:app --reload
```

*The API will be live at `http://localhost:8000/api`.*

---

## 2. Start the Modern Portal (Dashboard)

The frontend is a Next.js 14 App Router project located in the `portal/` directory. It handles Authentication via NextAuth.js and hosts the User and Creator Admin consoles.

**Command:**
```bash
# Open a new terminal tab and navigate to the portal root
cd portal/

# Install the necessary UI dependencies
npm install

# Start the development server
npm run dev
```

*The Portal will be live at `http://localhost:3000/`.*

---

## 3. Run the Automated Python Verification Tests

We built three robust Python integration test suites that you can run manually to verify the database and endpoints are functioning correctly.

Make sure the backend server (Step 1) is running before you execute these:

```bash
# In a new terminal, from the project root:
cd /home/avi/aviroop/NeuroSleepNet

# Test 1: Verifies the Memory logic works (Writes memories, retrieves them accurately)
uv run python3 tests/validation/validate_memory_v2.py

# Test 2: Verifies the User & Admin Analytics endpoints return the correct figures
uv run python3 tests/validation/validate_metrics.py

# Test 3: Verifies your Safety limiters (GDPR Purge mapping, PII scrubbing, Quota limits)
uv run python3 tests/validation/validate_safety.py
```

---

## 4. Test APIs Manually via Postman

If you want to manually test the API payloads without writing code, we built a JSON file that integrates directly into Postman.

1. Open Postman.
2. Click **Import** (Top left corner).
3. Select the file located at: `/home/avi/aviroop/NeuroSleepNet/neurosleepnet_postman_collection.json`
4. This will instantly build a "NeuroSleepNet V2 Memory Middleware" folder in Postman with 5 pre-configured endpoints ready to fire against `localhost:8000`.
