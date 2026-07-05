import unittest

import optimizer


class OptimizerTests(unittest.TestCase):
    def test_flatten_course_codes(self):
        self.assertEqual(
            optimizer.flatten_course_codes([[['BE30000']], ['AGEC31000'], 'HORT31800']),
            ['BE30000', 'AGEC31000', 'HORT31800'],
        )

    def test_format_and_clean_notes(self):
        self.assertEqual(optimizer.format_course("ACCT20100"), "ACCT 20100")
        self.assertEqual(
            optimizer.clean_notes(["** NOT overlap with X", "^50% of credits"]),
            ["NOT overlap with X", "50% of credits"],
        )

    def test_major_restriction_applies_only_on_matching_sentence(self):
        text = "This minor is not available to Computer Science students. Another sentence mentions Computer Science only as an example."
        self.assertTrue(optimizer.major_restriction_applies("Computer Science", text))
        self.assertFalse(optimizer.major_restriction_applies("Mechanical Engineering", text))
        self.assertFalse(optimizer.major_restriction_applies("None", text))

    def test_evaluate_formula_and_pool_sections(self):
        formula = {
            "title": "Required Courses",
            "kind": "formula",
            "required": 2,
            "groups": [
                [["ACCT20100"]],
                [["ACCT20000"], ["ACCT21200"]],
            ],
        }
        pool = {
            "title": "Select from B, C, D, or E (6 credits)",
            "kind": "pool",
            "required": 2,
            "options": ["AAE20000", "HIST27100", "ENGL30000", "ART20000"],
            "children": [],
        }

        formula_result = optimizer.evaluate_section(formula, {"ACCT20100", "ACCT21200"})
        pool_result = optimizer.evaluate_section(pool, {"AAE20000"})

        self.assertEqual(formula_result["completed"], 2)
        self.assertEqual(formula_result["taken_codes"], ["ACCT20100", "ACCT21200"])
        self.assertEqual(pool_result["completed"], 1)
        self.assertEqual(pool_result["remaining_options"], ["ART20000", "ENGL30000", "HIST27100"])

    def test_evaluate_formula_section_honors_exclusions(self):
        section = {
            "title": "C. Communication Course - 20000 level or higher (3 credits)",
            "kind": "formula",
            "required": 1,
            "groups": [[['COM20000']], [['COM21700']]],
            "excluded_codes": ['COM21700'],
        }

        only_excluded = optimizer.evaluate_section(section, {"COM21700"})
        valid_course = optimizer.evaluate_section(section, {"COM20000"})

        self.assertEqual(only_excluded["completed"], 0)
        self.assertEqual(valid_course["completed"], 1)
        self.assertEqual(valid_course["taken_codes"], ["COM20000"])

    def test_summarize_and_sort_minor_results(self):
        minors = [
            {
                "name": "Minor A",
                "link": "https://example.com/a",
                "sections": [
                    {
                        "title": "Required Courses",
                        "kind": "formula",
                        "required": 2,
                        "groups": [[["ACCT20100"]], [["ACCT20000"], ["ACCT21200"]]],
                    }
                ],
                "notes": ["50% of credits must come from Purdue."],
                "restriction_text": "",
            },
            {
                "name": "Minor B",
                "link": "https://example.com/b",
                "sections": [
                    {
                        "title": "Select from B, C, D, or E (6 credits)",
                        "kind": "pool",
                        "required": 2,
                        "options": ["AAE20000", "HIST27100", "ENGL30000"],
                        "children": [],
                    }
                ],
                "notes": [],
                "restriction_text": "",
            },
        ]

        taken = {"ACCT20100", "ACCT21200", "AAE20000"}
        results = [optimizer.summarize_minor(minor, taken, major="None") for minor in minors]
        results = [result for result in results if result is not None]
        sorted_results = optimizer.sort_minor_results(results)

        self.assertEqual([result["name"] for result in sorted_results], ["Minor A", "Minor B"])
        self.assertEqual(optimizer.residency_requirement(4, minors[0]["notes"]), (50, 2, 2))

    def test_summarize_minor_handles_deeply_nested_groups(self):
        minor = {
            "name": "Agricultural Engineering Technology and Management Minor",
            "link": "https://example.com/ag",
            "sections": [
                {
                    "title": "Selective Courses (12 credits)",
                    "kind": "formula",
                    "required": 4,
                    "groups": [
                        [[["BE30000"]]],
                        [["AGEC31000"]],
                        [["HORT31800"], ["HORT31900"]],
                    ],
                }
            ],
            "notes": [],
            "restriction_text": "",
        }

        summary = optimizer.summarize_minor(minor, {"BE30000", "HORT31900"}, major="None")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["completed"], 2)
        self.assertIn("BE30000", summary["taken_codes"])
        self.assertIn("HORT31900", summary["taken_codes"])


if __name__ == "__main__":
    unittest.main()