# How to use this repo

Personal study material. The example environment, Harborlight Logistics, is fictional.

## 1. Set up

Python 3.11 or newer. The tools use only the standard library. pytest is only needed for tests.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Run every command from the repository root.

## 2. Explore a baseline

```bash
python -m src.baseline_selector --baseline moderate --summary      # counts per family
python -m src.baseline_selector --baseline moderate --family IA    # rows for one family (CSV)
python -m src.baseline_selector --baseline low --no-enhancements   # base controls only
python -m src.baseline_selector --baseline high --diff-from moderate
```

Output is CSV, so you can redirect it to a file: `... > moderate_ia.csv`.

Typical questions this answers:

- *"We are moving a system from Low to Moderate. What's new?"* Use `--baseline moderate --diff-from low`, which returns 138 controls.
- *"Which Audit controls apply at High?"* Use `--baseline high --family AU`.

## 3. Go from 800-171r3 to 800-53

Each 800-171r3 requirement was derived from one or more 800-53 Rev. 5 controls. To list them:

```bash
python -m src.baseline_selector --from-171 03.05.03 03.13.11
```

This helps when a contractor already implements 800-171 and wants to know which 800-53 controls that work relates to. A source control is where a requirement *came from*. Meeting the requirement does not necessarily satisfy the full 800-53 control, because 800-171 tailors controls. NIST's CUI Overlay on the [800-171r3 page](https://csrc.nist.gov/pubs/sp/800/171/r3/final) shows that tailoring.

## 4. Run the coverage report

```bash
python -m src.coverage_report --baseline moderate
python -m src.coverage_report --baseline high --output high_coverage.md
```

The report lists:

1. Baseline controls that at least one detection supports, and which detections.
2. Coverage by family.
3. Mapped controls that the baseline does not select, such as SC-41 at Moderate.
4. 800-171r3 requirements whose source controls are touched.

How to read it: a detection *supports* a control by producing monitoring evidence. It never satisfies a control alone. Coverage uses exact IDs, so a detection mapped to `AC-2(4)` does not count toward `AC-2`.

## 5. Use the Splunk searches

Each file in `detections/splunk/` starts with a comment block that lists purpose, data source, mapped controls, and tuning notes.

The searches assume:

- Windows event logs in an index named `wineventlog`. Change this to match your environment, or use a macro.
- Field names as extracted by the Splunk Add-on for Microsoft Windows (XML rendering). Some field names differ with classic rendering.
- Required audit policies are enabled, for example "Audit PNP Activity" for USB events.

Try them in a lab, such as a Splunk free or developer instance with a test Windows VM. Never run them on data you are not authorized to access.

## 6. Add a detection

1. Write `detections/splunk/<name>.spl`. Copy the header format from an existing file, including the `Controls:` line and the line that says the environment is fictional.
2. Add one row per control to `data/detections_to_controls.csv`: `detection,spl_file,control_53,rationale`.
3. Run `python -m pytest`. The tests check that:
   - every control ID exists in the Rev. 5 catalog
   - the `Controls:` header matches the CSV rows
   - every `.spl` file is mapped, and every mapped file exists
   - no IP address literals appear in the searches

## 7. Rebuild the NIST data

When NIST issues a new release:

```bash
git clone --depth 1 https://github.com/usnistgov/oscal-content.git /tmp/oscal-content
python -m scripts.build_data /tmp/oscal-content
python -m pytest
```

If baselines change, the count test in `tests/test_data_integrity.py` will fail on purpose. Update the expected numbers from the new SP 800-53B release, then update the versions table in the README.
