# CPU CI runs

c28751d push39921200482 and PR39921249503 failed before test execution because GitHub Runner split single-quoted Docker health command. f403b69 push39921437593 attempt1 was cancelled by shared concurrency, then the Builder cancelled the pending PR39921444390, leaving no run. The Builder reran push39921437593 attempt2; full CPU job succeeded08:03:19Z–08:05:46Z, required CPU step68s. Later repaired candidate and final exact-SHA runs remain separately identified. Initialization failures/cancellations are retained, not counted as successful tests.
