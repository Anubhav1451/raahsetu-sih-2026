# RaahSetu (राहसेतु) — Official Authority Credentials & RBAC Roles

> **For SIH 2026 Grand Finale Evaluation & Role-Based Access Control (RBAC) Proof**

## Live Supabase Auth Accounts (verified working sign-in)

These accounts exist in the project's Supabase Auth with provisioned profile roles.
Email addresses use a real deliverable domain because Supabase rejects the
fictional `raahsetu.in` domain on signup.

| Role | Official Email | Demo Password | Official Name & Designation | Region / Corridor | Status |
|---|---|---|---|---|---|
| **`REVIEWER`** | `sdrf.arunachal.raahsetu@gmail.com` | Stored in local secret manager | Insp. Tenzing Norbu (SDRF - West Kameng Div) | arunachal-pradesh | ✅ created |
| **`REVIEWER`** | `pwd.assam.raahsetu@gmail.com` | Stored in local secret manager | Er. Bhupen Barman (Executive Engineer, Assam PWD) | assam | ✅ created |
| **`DISPATCHER`** | `dispatcher.ner.raahsetu@gmail.com` | Stored in local secret manager | Rajesh Sharma (Regional Freight Logistics Controller) | assam | ✅ created |
| **`DRIVER`** | `driver.anup.raahsetu@gmail.com` | Stored in local secret manager | Ranjit Gogoi (Freight Captain, AS-01-GB-4821) | assam | ✅ created |
| **`ADMIN`** | `admin.raahsetu.hq@gmail.com` | Stored in local secret manager | State Emergency Control Officer | All 8 NE States | ✅ created |

> All authority accounts have been provisioned and confirmed in Supabase Auth.
> Logins have been verified with 200 OK tokens.
> Passwords are intentionally never stored in this document or source code.

---

## Role Permission Matrix (Enforced by PostGIS Row Level Security)

| Capability | `driver` | `reviewer` (SDRF/PWD) | `dispatcher` | `admin` |
|---|:---:|:---:|:---:|:---:|
| Calculate Route (Fastest vs Risk-A*) | ✅ | ✅ | ✅ | ✅ |
| View Live Weather & Microclimate | ✅ | ✅ | ✅ | ✅ |
| Submit Field Report (Pending State) | ✅ | ✅ | ✅ | ✅ |
| Stream Real Hardware GPS Telemetry | ✅ | ❌ | ❌ | ✅ |
| **Authority Verify Field Report (Close / Penalize Edge)** | ❌ | ✅ | ❌ | ✅ |
| **Broadcast Emergency Driver Dispatch Alert** | ❌ | ❌ | ✅ | ✅ |
| Manage Fleet Delivery Allocations | ❌ | ❌ | ✅ | ✅ |
| Access Cross-Regional Data Across All 8 States | ❌ | ❌ (Own State Only) | ✅ | ✅ |

---

## 1-Click UI Quick Login
In the web dashboard, clicking **'Quick Login'** allows the presenter to switch between **SDRF Reviewer**, **Fleet Dispatcher**, and **Driver** in 1 click without manual typing.
