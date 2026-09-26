# How the broader chat setup works

This is a plain-language overview of a separate local chat assistant. The public code in this repository only exports a user's own local history; it does not contain the assistant, reply, forwarding, or sending components.

## What happens to a message

**Receiving:** The local service checks the account's message database for new entries. The app may still be writing a message when the service looks, so it reads a consistent snapshot and remembers where it got to. On the next pass it continues from there instead of importing the same messages again.

**Choosing whether to reply:** A small rule layer checks who sent the message, which conversation it belongs to, and whether the person actually mentioned the assistant. It can ignore messages outside the configured group or direct-message scope. This keeps ordinary conversation from triggering an answer.

**Writing an answer:** The assistant gets only a short window of recent messages from that conversation—normally the latest 15. If someone quotes an older message or asks about something that needs background, the service can retrieve the relevant public reference separately. The model returns text; it does not get general-purpose access to the computer or messaging account.

**Forwarding:** A separate rule checks whether an incoming message is eligible for forwarding, including whether it is marked silent. Eligible messages are copied to the configured destination group. A saved message ID prevents the same item from being forwarded repeatedly. Media may be represented by a short notice instead of being copied as if it were text.

**Sending:** In the separate local deployment, a sending adapter passes approved text to the logged-in client and checks the local message record for evidence that it was accepted. That adapter is intentionally absent from this repository. Sending behavior depends on the exact client build and is not a supported feature of this history exporter.

## What went wrong and what changed

- **The wrong logged-in account could be selected.** A display name alone was not enough when more than one account was open. The service was changed to require an explicit account and check it against the local database before reading.
- **New messages sometimes appeared to be missing.** Some recent database changes live in SQLite's side log until a transaction is finished. Reading only the main file can show an older view. The reader now checks the main file and side log together, and retries if they change during copying.
- **Polling can create duplicates.** The service now saves a progress marker and message ID, so a restart can continue safely and recognize messages already stored.
- **A send request is not proof of delivery.** A local call can return before the message is visible in the account's own history. The private sender therefore checks for a matching new record and treats an unclear result as uncertain instead of blindly sending again.
- **Too much conversation history makes answers noisy and exposes more than needed.** The companion assistant uses the latest 15 messages by default and fetches older public material only when the question calls for it.
- **Client updates can change internal behavior.** Database formats and local adapters may stop matching after an update. The deployment must be rechecked against the new build; this repository does not claim cross-version support.
- **Frequent automatic actions can amplify failures.** The broader service uses persistent request IDs, pacing, and bounded retries so a temporary problem does not turn into repeated sends. This repository exports files only and runs no background polling or automatic messaging.

## Boundary

This overview does not publish account keys, real chat records, private paths, low-level process-control instructions, or ways to avoid platform safeguards. It is not a promise that unofficial client integrations will work with every version. For this public package, the only implemented capability is a user-triggered, read-only export of local message tables.
