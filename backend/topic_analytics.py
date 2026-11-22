"""Topic analytics: tables and the skill matrix. Owner: Bahodirjon.

No SQL and no web code: these functions only take tables (pandas
DataFrames) and calculate, so they are easy to test.
"""

import numpy as np
import pandas as pd

from backend.config.business_rules import TopicStatus

HAS_SKILL = 1


def completed_topics(records: pd.DataFrame) -> pd.DataFrame:
    """Keep only the topic records whose status is Completed."""
    is_completed = records["status"] == TopicStatus.COMPLETED.value
    return records[is_completed]


def student_skill_pairs(records: pd.DataFrame) -> pd.DataFrame:
    """Unique (student_id, skill) pairs.

    Two finished topics can teach the same skill; the student still
    has that skill only once.
    """
    return records[["student_id", "skill"]].drop_duplicates()


def build_skill_matrix(
    student_ids: list[int], skills: list[str], pairs: pd.DataFrame
) -> np.ndarray:
    """A 0/1 NumPy matrix: row = student, column = skill.

    matrix[row, column] is 1 when student_ids[row] has skills[column].
    """
    matrix = np.zeros((len(student_ids), len(skills)), dtype=int)
    # get_indexer turns each ID / skill name into its row / column
    # number, so all the 1s are placed in one step without a loop.
    rows = pd.Index(student_ids).get_indexer(pairs["student_id"])
    columns = pd.Index(skills).get_indexer(pairs["skill"])
    is_known = (rows >= 0) & (columns >= 0)  # -1 means "not in the list"
    matrix[rows[is_known], columns[is_known]] = HAS_SKILL
    return matrix
