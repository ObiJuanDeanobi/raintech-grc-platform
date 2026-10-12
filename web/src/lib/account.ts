/**
 * The signed-in account. The local app has one account today; every sign-off
 * (approving a Profile version, issuing a report) is recorded as this person.
 */
export const ACCOUNT = { id: "johnathan", name: "Johnathan" } as const;
export const ACCOUNT_NAME = ACCOUNT.name;
