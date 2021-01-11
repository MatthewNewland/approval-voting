"""This implements both standard approval voting (single-winner), as well as
Sequential Proportional Approval Voting (https://en.wikipedia.org/wiki/Sequential_proportional_approval_voting).

The same function, approval_election, serves both purposes, since the latter reduces to the former
in the single-seat case.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from io import StringIO
from tabulate import tabulate
from typing import List, Union
from pathlib import Path
import csv
import os
import argparse


@dataclass
class Candidate:
    name: str

    def __repr__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class Ballot:
    approved_candidates: List[Candidate]
    weight: Union[int, float] = 1  #pylint:disable=unsubscriptable-object


@dataclass
class Round:
    """The results of one round of candidate-election--each round elects one candidate and
    then the ballots are reweighted"""
    winner: Candidate
    scores: Counter[Candidate]
    weighted_votes: float
    #ballots: List[Ballot]

    def __repr__(self) -> str:
        """Console-based representation of the results of this round of voting."""
        headers = ["Name", "Approve", "Do Not Approve", "Percent Approve", "Percent Do Not Approve"]
        table = []
        win = True
        votes = self.weighted_votes
        for candidate, score in self.scores.most_common():
            if candidate == self.winner:
                win = " (winner)"
            else:
                win = ""
            table.append([candidate.name + win, score, votes - score, score/votes, (votes-score)/votes])

        return tabulate(table, headers=headers, floatfmt=(None, "", "", ".2%", ".2%"))


@dataclass
class Result:
    """The results of an approval election"""
    winners: List[Candidate]
    rounds: List[Round]
    ballots: List[Ballot]

    def __repr__(self) -> str:
        out = StringIO()
        print(f"{len(self.ballots)} ballots cast", file=out)
        print("Columns represent weighted preferences.", file=out)

        for i, round in enumerate(self.rounds):
            print(f"Round {i + 1}:", file=out)
            print(round, file=out)

        for i, winner in enumerate(self.winners):
            print(f"Seat {i + 1}: {winner.name} wins", file=out)

        return out.getvalue().rstrip()


def parse_ballots(ballot_file: os.PathLike) -> List[Ballot]:
    """Takes a CSV file formatted as follows:

    `number,cand1,cand2,cand3,...`

    where `number` is the number of ballots approving exactly these candidates.

    If the first element of a row is not interpretable as a number, it will
    be treated as the name of a candidate.
    This allows us to avoid repetition for toy cases, while still allowing for data
    to be collected from a variety of sources.
    """
    ballots = []
    # See https://stackoverflow.com/questions/14158868/python-skip-comment-lines-marked-with-in-csv-dictreader
    def decomment(csvfile):
        for row in csvfile:
            raw = row.split('#')[0].strip()
            if raw:
                yield row

    with Path(ballot_file).open() as handle:
        reader = csv.reader(decomment(handle))
        for row in reader:
            first, *rest = row
            try:
                number = int(first)
            except ValueError:
                number = 1
            approved_candidates = [Candidate(name.strip()) for name in rest]

            for _ in range(number):
                ballots.append(Ballot(approved_candidates))

    return ballots


def approval_election(ballots: List[Ballot], seats: int = 1) -> Result:
    """Run an approval election.

    Note that BALLOT ORDER MATTERS, especially for clone candidates! The algorithm below,
    in the case of a tie between two candidates, will return the one who is seen first.
    """
    rounds = []
    winners = []
    while len(winners) < seats:
        scores = Counter()
        for ballot in ballots:
            for candidate in ballot.approved_candidates:
                if candidate in winners:
                    continue
                scores[candidate] += ballot.weight

        (winner, _), *_ = scores.most_common()

        winners.append(winner)
        rounds.append(Round(winner, scores.copy(), sum(b.weight for b in ballots)))

        for ballot in ballots:
            m = sum(1 for c in ballot.approved_candidates if c in winners)
            ballot.weight = 1 / (1 + m)

    return Result(winners, rounds, ballots)


def main():
    parser = argparse.ArgumentParser(description="Approval election command line tool")
    parser.add_argument('ballot_file', help="CSV file with ballot data")
    parser.add_argument('--seats', type=int, default=1, help="Number of winners (default 1)")
    args = parser.parse_args()

    ballots = parse_ballots(args.ballot_file)
    print(approval_election(ballots, args.seats))


if __name__ == '__main__':
    main()
