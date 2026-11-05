# Requirements — one deliberately broken row per rule

Rows R-901…R-910 each violate exactly one rule; the selftest asserts the message.

| id | statement | attaches to | assertion | evidence |
|---|---|---|---|---|
| R-901 | zero assertions in the assertion column | module: MOD-01 | — | fact: FACT-01 |
| R-902 | two assertions in one row | module: MOD-01 | test: TestA test: TestB | fact: FACT-01 |
| R-903 | nothing in the evidence column | module: MOD-01 | test: TestA | |
| R-904 | evidence cites a fact that does not exist | module: MOD-01 | test: TestA | fact: FACT-99 |
| R-905 | prose mentions (see check: above) instead of an assertion | module: MOD-01 | — | fact: FACT-01 |
| R-906 | assertion target is a description | module: MOD-01 | test: it rejects expired tokens | fact: FACT-01 |
| R-907 | only four columns | module: MOD-01 | test: TestA |
| R-908 | attach column names no module | see the statement above | test: TestA | fact: FACT-01 |
| R-909 | claim names a module that does not exist | module: MOD-77 | test: TestA | fact: FACT-01 |
| R-910 | duplicate id | module: MOD-01 | test: TestA | fact: FACT-01 |
| R-910 | duplicate id | module: MOD-01 | test: TestB | fact: FACT-01 |
