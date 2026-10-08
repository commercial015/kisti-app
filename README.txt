KISTI HISAB PROFESSIONAL
=========================

এটি Windows-এর জন্য কিস্তি/Loan/DPS হিসাব ব্যবস্থাপনার desktop application project।

মূল সুবিধা:
- Customer management
- Grameen / Bank / Personal loan
- Daily / Weekly / Monthly installment
- Interest + service charge
- Partial/full collection
- Cash / Bank / bKash / Nagad
- DPS schedule
- Dashboard
- CSV reports
- SQLite database
- Backup
- Organization settings
- Login

Default login:
Username: admin
Password: 1234

Windows EXE:
1. Windows PC-তে Python 3.11+ install করুন।
2. Add Python to PATH নির্বাচন করুন।
3. build_exe.bat double-click করুন।
4. dist\KistiHisabProfessional.exe পাওয়া যাবে।

GitHub থেকে EXE:
1. এই project GitHub repository-তে upload করুন।
2. .github/workflows/windows-build.yml automatically Windows runner-এ build করবে।
3. GitHub Actions-এর Artifacts থেকে ZIP download করা যাবে।

নোট:
Grameen/Bank/DPS-এর হিসাব এখানে configurable projection; নির্দিষ্ট প্রতিষ্ঠানের official formula নয়।
