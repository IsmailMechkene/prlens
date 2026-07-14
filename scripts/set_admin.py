"""Grant or revoke the administrator role on a PRLens account.

This is the *only* way a user becomes an admin. There is deliberately no endpoint
and no button for it: an admin surface that can mint more admins turns a single
compromised admin session — or one bug in the role check — into a permanent
privilege-escalation path. Promotion is therefore an out-of-band action, taken by
somebody who already has database credentials.

The user must have signed in through GitHub at least once, so that there is a row
to promote.

Usage (from the project root, with DATABASE_URL set):

    python -m scripts.set_admin --handle IsmailMechkene
    python -m scripts.set_admin --handle @IsmailMechkene --revoke
    python -m scripts.set_admin --github-id 12345678
    python -m scripts.set_admin --list
"""

import argparse
import sys

from database.connection import SessionLocal
from database.models import ROLE_ADMIN, ROLE_USER, User


def _find_user(db, handle: str | None, github_id: int | None) -> User | None:
    if github_id is not None:
        return db.query(User).filter(User.github_id == github_id).first()

    # Handles are stored with the leading "@" (see the OAuth callback), but nobody
    # types it, so accept either form.
    stored = handle if handle.startswith("@") else f"@{handle}"
    return db.query(User).filter(User.handle == stored).first()


def _list_users(db) -> int:
    users = db.query(User).order_by(User.id).all()
    if not users:
        print("No users yet — nobody has signed in through GitHub.")
        return 0

    width = max(len(user.handle) for user in users)
    for user in users:
        marker = "*" if user.role == ROLE_ADMIN else " "
        print(f"{marker} {user.handle:<{width}}  id={user.github_id:<12} {user.role}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--handle", help="GitHub login, with or without the leading @")
    target.add_argument("--github-id", type=int, help="GitHub numeric user id")
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Demote back to an ordinary user instead of promoting",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List every account and its role, then exit (admins marked with *)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            return _list_users(db)

        if not args.handle and args.github_id is None:
            parser.error("give --handle or --github-id (or --list)")

        user = _find_user(db, args.handle, args.github_id)
        if not user:
            who = args.handle or f"github_id={args.github_id}"
            print(f"No account for {who}.", file=sys.stderr)
            print(
                "They have to sign in to the dashboard once before they can be "
                "promoted — the row does not exist until then.",
                file=sys.stderr,
            )
            return 1

        role = ROLE_USER if args.revoke else ROLE_ADMIN
        if user.role == role:
            print(f"{user.handle} is already {role!r}. Nothing to do.")
            return 0

        # Demoting the last admin would leave the deployment with no way back into
        # the admin dashboard short of another run of this script — which is fine,
        # but it should not happen by accident.
        if args.revoke:
            admins = db.query(User).filter(User.role == ROLE_ADMIN).count()
            if admins <= 1:
                print(
                    f"{user.handle} is the only admin. Promote somebody else first, "
                    "or re-run this script later to get the role back.",
                    file=sys.stderr,
                )
                return 1

        was = user.role
        user.role = role
        db.commit()
        print(f"{user.handle}: {was} -> {role}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
