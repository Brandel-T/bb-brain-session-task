# Datasheet extraction case

A customer sends us technical datasheets from their suppliers and wants a comparison table.
Right now someone opens every PDF and types the values into Excel.

Build a script that does it for them. For each of the ten datasheets, extract four values:
- **manufacturer**,
- **model**, 
- **IP rating**, and
- **operating temperature range**.

Write the result to a CSV.

You create the bot and the API key yourself in the demo environment. The endpoints you need are
listed below. How you use them is up to you.

## What you have

- `datasheets/`: the ten PDFs
- `API-ENDPOINTS.md`: the calls you need. Create a conversation, upload a file, check
  processing status, send a message, delete a conversation
- `.env.example`: copy to `.env` and fill in your API key and the ID of the bot you created

## Time budget

Plan for about three hours. If you develop without AI coding tools, expect a bit more. Use them
if you want to, we do too, and we will ask you how you used them.

## Language

TypeScript or Python, whichever suits you.

## What to bring

Your script and the CSV it produced. You do not need to prepare a presentation. We are
interested in how you approached it, what gave you trouble, and which problems or improvements
you see.

If something here is unclear, make an assumption, tell us it was one, and tell us how you would
check it with the customer.
