# Auditoría enfocada: dashboard + watchdog + bot telegram

- Fecha UTC: 2026-09-14T07:36:41.489567Z
- Scripts auditados: 25
- dashboard: 10
- watchdog: 4
- telegram-bot: 10
- other: 1

| # | component | file | syntax | risk | score | exceptE | bare | shell | os.system | eval | exec | req_no_timeout | telegram_refs | main |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | dashboard | /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | dashboard | /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/agent_tab.py | ok | LOW | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | dashboard | /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/api.py | ok | MEDIUM | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 94 | 0 |
| 4 | dashboard | /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/app.py | ok | LOW | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 1 |
| 5 | dashboard | /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/ask_faq.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| 6 | dashboard | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/dashboard/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | dashboard | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/dashboard/agent_tab.py | ok | LOW | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 | dashboard | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/dashboard/api.py | ok | MEDIUM | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 94 | 0 |
| 9 | dashboard | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/dashboard/app.py | ok | LOW | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 1 |
| 10 | dashboard | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/dashboard/ask_faq.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| 11 | other | /home/deamon/consensus-expert-agent/alert_queue.py | ok | LOW | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 1 |
| 12 | telegram-bot | /home/deamon/consensus-expert-agent/telegram_bot.py | ok | MEDIUM | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 102 | 1 |
| 13 | telegram-bot | /home/deamon/workspaces/sentinel_omega/infrastructure/api/telegram.py | ok | LOW | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 60 | 0 |
| 14 | telegram-bot | /home/deamon/workspaces/sentinel_omega/infrastructure/messaging/consenso_vigilante.py | ok | MEDIUM | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 |
| 15 | telegram-bot | /home/deamon/workspaces/sentinel_omega/infrastructure/telegram/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| 16 | telegram-bot | /home/deamon/workspaces/sentinel_omega/infrastructure/telegram/bot.py | ok | LOW | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 0 |
| 17 | telegram-bot | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/api/telegram.py | ok | LOW | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 60 | 0 |
| 18 | telegram-bot | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/messaging/consenso_vigilante.py | ok | MEDIUM | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 |
| 19 | telegram-bot | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/telegram/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| 20 | telegram-bot | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/telegram/bot.py | ok | LOW | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 0 |
| 21 | telegram-bot | /home/deamon/workspaces/sentinel_omega/tests/test_consenso_vigilante.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| 22 | watchdog | /home/deamon/workspaces/sentinel_omega/infrastructure/watchdog/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 23 | watchdog | /home/deamon/workspaces/sentinel_omega/infrastructure/watchdog/network_watchdog.py | ok | LOW | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 1 |
| 24 | watchdog | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/watchdog/__init__.py | ok | LOW | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 25 | watchdog | /home/deamon/workspaces/sentinel_omega/sentinel_omega/infrastructure/watchdog/network_watchdog.py | ok | LOW | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 1 |