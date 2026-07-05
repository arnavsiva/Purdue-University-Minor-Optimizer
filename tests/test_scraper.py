import unittest
from unittest.mock import patch

import scraper


MINORS_INDEX_HTML = """
<html>
  <body>
    <main>
      <a href="/preview_program.php?catoid=19&poid=111">Accounting Minor</a>
      <a href="/preview_program.php?catoid=19&poid=222">Accounting, BS</a>
      <a href="/preview_program.php?catoid=19&poid=333">Aerospace Studies Minor</a>
      <a href="/preview_program.php?catoid=19&poid=444">Minor in Something</a>
    </main>
  </body>
</html>
"""


MAJORS_PAGE_HTML = """
<html>
  <body>
    <main>
      <h2>Accounting</h2>
      <a href="https://admissions.purdue.edu/majors/accounting/">LEARN MORE</a>
      <h2>African American Studies</h2>
      <a href="https://admissions.purdue.edu/majors/african-american-studies/">LEARN MORE</a>
      <h2>Follow Us</h2>
      <a href="https://www.facebook.com/PurdueUniversity/">Facebook</a>
    </main>
  </body>
</html>
"""


ACCOUNTING_MINOR_HTML = """
<html>
  <body>
    <main>
      <h1>Accounting Minor</h1>
      <h2>Requirements for the Minor (15 credits)</h2>
      <h3>Required Courses (9-12 credits)</h3>
      <hr>
      <ul>
        <li>ACCT 20100 - Management Accounting I Credit Hours: 3.00</li>
        <li></li>
        <li>ACCT 20000 - Introductory Accounting Credit Hours: 3.00 or</li>
        <li>ACCT 21200 - Business Accounting Credit Hours: 3.00</li>
        <li></li>
        <li>ACCT 35000 - Intermediate Accounting I Credit Hours: 3.00 and</li>
        <li>ACCT 35100 - Intermediate Accounting II Credit Hours: 3.00</li>
        <li>OR</li>
        <li>ACCT 35300 - Intermediate Accounting For Non-Accounting Majors Credit Hours: 3.00</li>
      </ul>
      <h3>Additional Courses (3-6 credits)</h3>
      <hr>
      <ul>
        <li>MGMT 20000 - Management Fundamentals Credit Hours: 3.00</li>
        <li>or</li>
        <li>MGMT 20100 - Management Concepts Credit Hours: 3.00</li>
      </ul>
      <h2>Notes</h2>
      <ul>
        <li>50% of credits for CLA minors must come from Purdue University.</li>
      </ul>
      <h2>Disclaimer</h2>
      <p>This minor is not available to Example Major students.</p>
    </main>
  </body>
</html>
"""


AFRICAN_AMERICAN_MINOR_HTML = """
<html>
  <body>
    <main>
      <h1>African American Studies Minor</h1>
      <h2>Requirements for the Minor (15 credits)</h2>
      <h3>Required Foundation Courses (9 credits)</h3>
      <h4>A. African American Studies Foundation Courses</h4>
      <hr>
      <ul>
        <li>AAS 27100 - Introduction To African American Studies (UCC: HUM) Credit Hours: 3.00</li>
        <li>AAS 37100 - The African American Experience Credit Hours: 3.00</li>
        <li>AAS 37300 - Issues In African American Studies Credit Hours: 3.00</li>
      </ul>
      <h3>Select from B, C, D, or E (6 credits)</h3>
      <h4>B. Social Science Courses Related to Africa or the African Diaspora</h4>
      <hr>
      <ul>
        <li>AAE 20000 - Example Social Science Credit Hours: 3.00</li>
      </ul>
      <h4>C. History Courses Related to Africa or the African Diaspora</h4>
      <hr>
      <ul>
        <li>HIST 27100 - Example History Credit Hours: 3.00</li>
      </ul>
      <h4>D. English Courses Related to Africa or the African Diaspora</h4>
      <hr>
      <ul>
        <li>ENGL 30000 - Example English Credit Hours: 3.00</li>
      </ul>
      <h4>E. Visual and Performing Arts Courses Related to Africa or the African Diaspora</h4>
      <hr>
      <ul>
        <li>ART 20000 - Example Arts Credit Hours: 3.00</li>
      </ul>
      <h2>Notes</h2>
      <ul>
        <li>50% of credits for CLA minors must come from Purdue University.</li>
      </ul>
    </main>
  </body>
</html>
"""


COMMUNICATION_MINOR_HTML = """
<html>
  <body>
    <main>
      <h1>Communication Minor</h1>
      <h2>Requirements for the Minor (15 credits)</h2>
      <h3>A. Required Course (3 credits)</h3>
      <ul>
        <li>COM 11400 - Fundamentals Of Speech Communication Credit Hours: 3.00</li>
        <li>COM 21700 - Science Writing And Presentation Credit Hours: 3.00</li>
      </ul>
      <h3>B. Foundations in Communication (3 credits)</h3>
      <ul>
        <li>COM 10200 - Introduction To Communication Theory Credit Hours: 3.00</li>
        <li>COM 20400 - Critical Perspectives On Communication Credit Hours: 3.00</li>
        <li>COM 31800 - Principles Of Persuasion Credit Hours: 3.00</li>
      </ul>
      <h3>C. Communication Course - 20000 level or higher (3 credits)</h3>
      <ul>
        <li>COM 20000 - 59999 (any course EXCEPT COM 21700, which cannot be counted to satisfy category C)</li>
      </ul>
      <h3>D. Upper Level Communication Courses (6 credits)</h3>
      <ul>
        <li>COM 30000 - 59999 (any course)</li>
      </ul>
      <h2>Notes</h2>
      <ul>
        <li>A grade of “C-” or better for this minor. The P/NP option is not available to complete this minor.</li>
      </ul>
    </main>
  </body>
</html>
"""


class ScraperTests(unittest.TestCase):
    def test_get_minor_list_filters_only_minors(self):
        with patch("scraper._fetch_html", return_value=MINORS_INDEX_HTML):
            minors = scraper.get_minor_list()

        self.assertEqual(
            minors,
            [
                ("Accounting Minor", "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=111"),
                ("Aerospace Studies Minor", "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=333"),
                ("Minor in Something", "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=444"),
            ],
        )

    def test_get_majors_list_parses_current_page_layout(self):
        with patch("scraper._fetch_html", return_value=MAJORS_PAGE_HTML):
            majors = scraper.get_majors_list()

        self.assertEqual(majors, ["Accounting", "African American Studies"])

    def test_accounting_minor_parser_handles_or_and_and(self):
        with patch("scraper._fetch_html", return_value=ACCOUNTING_MINOR_HTML):
            sections, notes, restriction_text = scraper._get_requirements_from_minor_page(
                "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=111"
            )

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["title"], "Required Courses (9-12 credits)")
        self.assertEqual(sections[0]["kind"], "formula")
        self.assertEqual(sections[0]["required"], 3)
        self.assertEqual(
            sections[0]["groups"],
            [
                [["ACCT20100"]],
            [["ACCT20000"], ["ACCT21200"]],
                [["ACCT35000", "ACCT35100"], ["ACCT35300"]],
            ],
        )
        self.assertEqual(sections[1]["title"], "Additional Courses (3-6 credits)")
        self.assertEqual(notes, ["50% of credits for CLA minors must come from Purdue University."])
        self.assertIn("not available to Example Major students", restriction_text)

    def test_african_american_minor_parser_handles_nested_choices(self):
        with patch("scraper._fetch_html", return_value=AFRICAN_AMERICAN_MINOR_HTML):
            sections, notes, restriction_text = scraper._get_requirements_from_minor_page(
                "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=222"
            )

        self.assertEqual(
            [section["title"] for section in sections],
            [
                "A. African American Studies Foundation Courses",
                "Select from B, C, D, or E (6 credits)",
            ],
        )
        self.assertEqual(sections[0]["kind"], "formula")
        self.assertEqual(sections[0]["required"], 3)
        self.assertEqual(
            sections[0]["groups"],
            [[["AAS27100"]], [["AAS37100"]], [["AAS37300"]]],
        )
        self.assertEqual(sections[1]["kind"], "pool")
        self.assertEqual(sections[1]["required"], 2)
        self.assertEqual(len(sections[1]["children"]), 4)
        self.assertEqual(notes, ["50% of credits for CLA minors must come from Purdue University."])
        self.assertIn("50% of credits for CLA minors must come from Purdue University.", restriction_text)

    def test_communication_minor_parser_captures_exclusion(self):
        with patch("scraper._fetch_html", return_value=COMMUNICATION_MINOR_HTML):
            sections, notes, restriction_text = scraper._get_requirements_from_minor_page(
                "https://catalog.purdue.edu/preview_program.php?catoid=19&poid=34843"
            )

        c_section = next(section for section in sections if section["title"].startswith("C."))
        self.assertIn("COM21700", c_section.get("excluded_codes", []))
        self.assertEqual(
            notes[0],
            "A grade of “C-” or better for this minor. The P/NP option is not available to complete this minor.",
        )


if __name__ == "__main__":
    unittest.main()