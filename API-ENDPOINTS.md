# Blocky API: endpoints for this case

Base URL:

```
https://api.theblockbrain.ai/blocky/v2
```

The full reference for these endpoints is at
https://api.theblockbrain.ai/docs, section Knowledge Bots.

Your API key and the ID of the bot you created go into your `.env`
(copy `.env.example`). Every request below needs this header:

```
Authorization: Bearer <BB_TOKEN>
```

You do not need to send an organization header. Your key already carries the
organization it belongs to.

## 1. Create a conversation

```
POST {BB_URL}/cortex/active-bot/{BB_BOT_ID}/convo
Content-Type: application/json

{ "convoName": "<any name>" }
```

Response body: `{ "body": { "dataRoomId": "<convoId>" } }`. The `dataRoomId`
is the conversation ID you use in every call below.

## 2. Upload a file

```
POST {BB_URL}/cortex/conversation/{convoId}/attachment
Content-Type: multipart/form-data
```

Form fields: `attachment` (the file), `session_id` (any UUID).

Response body: `{ "body": { "_id": "...", "name": "...", "status": "..." } }`.

This call returns as soon as the upload is received, not once the bot has
read the file. See below.

## 3. Check processing status

```
GET {BB_URL}/cortex/conversation/{convoId}/attachment
```

Response body: `{ "body": [ { "_id": "...", "status": "..." } ] }`.

`status` is `IN_PROGRESS` or `LOADING` while the document is still being
read, and `COMPLETED`/`SUCCESS` or `ERROR`/`FAILED` once it's done. Poll this
endpoint until the attachment you uploaded leaves the in-progress state.

## 4. Send a message

```
POST {BB_URL}/cortex/completions/v2/user-input
Content-Type: application/json

{
  "convoId": "<convoId>",
  "content": "<your question>",
  "sessionId": "<any UUID>",
  "messageType": "user-question",
  "enableStreaming": false
}
```

Response body: `{ "body": { "content": "<bot's answer>" } }`.

## 5. Delete a conversation

```
DELETE {BB_URL}/cortex/conversation/{convoId}
```

No response body. Call this once you're done with a conversation, including
when something upstream failed.
