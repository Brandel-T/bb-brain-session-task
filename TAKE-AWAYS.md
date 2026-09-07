# My Key take aways

## Troubles/Problems
Actually, _None_.

However, the "traps" i noticed were:
- nuances in terms used in the datasheets, e.g. "IP Rating" vs "IP Code" etc. as the come from different manufacturers.
- multiple model variants in the datasheets (e.g. sheet 08: "metrion drives"), which required a more specific output format to the LLM to extract them as a list of dictionaries.

## My Approach

### Development

I first created the functions listed in [API-ENDPOINTS.md](/API-ENDPOINTS.md) (create convo, upload file, etc.) to interact with the BB's [API doc](https://api.theblockbrain.ai/docs).

### LLM chosen to power my bot

**Claude Sonnet 5**:

Config:
- creative freedom (temperature): `0.2` --> **Because of the possible synonyms of the key values from technical sheets**
- vocabulary range: `1.0` _(default)_
- topic variety: `0.0` _(default)_
- word variety: `0.0` _(default)_
- web search disabled --> _no need_

| Pros | Cons |
|------|------|
| good at extracting structured data from unstructured text | may be slower than other models |
| can handle complex instructions | has a limited context window |
| has a good understanding of technical language |  |
| Enough token for file processing: `1M` |  |
| Quality: `4.7` |  |
| Speed: `4.4` |  |
| Cost `3.6`: Maybe costly, but has a better cost-effectiveness ratio than other models, e.g. from Azure AI |  |

An alternative could have been **GPT 5.6 Luna**:

- Quality: `3.7`
- Speed: `4`
- Cost: `5`

> Justification for the choice of **Claude Sonnet 5** over **GPT 5.6 Luna**:
> ---
> The quality and cost-effectiveness ratio, as well as its ability to handle complex instructions and technical language.
> 
> 🧠💡 Most relevant for this task, as the datasheets contain **technical information** that needs to be **accurately extracted**.


⚠️Metrics according to the [Blocky API documentation](https://api.theblockbrain.ai/docs).

### Prompt Engineering

I used **role-task-context-output_format** prompt engineering technique to instruct the LLM to extract the required values from the datasheets.

- The **1rst version** of my user prompt (see `EXTRACTION_PROMPT_V1` in [extract.py](/extract.py)) didn't conver the case, where the technical data contain multiple model variants.

- The **2nd and last version** (see `EXTRACTION_PROMPT`) clearly specifies it, and instructs the LLM to extract the variants as a list of dictionaries, each containing the required values.

## Improvements

Maybe having an endpoint to read multiple attached files at once, instead of having to upload them one by one, would be a good improvement for the API.

⚠️ **Critique:** I wonder if it's scalable (at customer level) to have the LLM read multiple files at once, as it may exceed the context window, as the number of data sheets increases.

