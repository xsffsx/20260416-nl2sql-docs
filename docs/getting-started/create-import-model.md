---
sidebar_position: 3
title: Create and import a model
---

import useBaseUrl from '@docusaurus/useBaseUrl';

# Create and import a model

Use the Start guide to import one small model and confirm it in the ER diagram.

This guide uses one table:

```sql
CREATE TABLE public.fund_master (
  fund_code text PRIMARY KEY,
  fund_name text NOT NULL,
  risk_level integer,
  nav numeric(12,4),
  launched_on date
);
```

## 1. Choose DDL

Open **Modeling** and start the guide. In the Import panel, click **DDL**.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/01-select-ddl.png')}
    alt="Start guide highlighting the DDL source in the Modeling import panel"
  />
  <figcaption>Choose DDL in the Import panel.</figcaption>
</figure>

## 2. Check the preview

The guide fills the DDL editor with `fund_master`. The preview must show:

- **1 model**
- **5 columns**
- **0 relationships**

When the preview is valid, **Import** is enabled.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/02-preview-import.png')}
    alt="fund_master DDL with one model, five columns, zero relationships, and an enabled Import button"
  />
  <figcaption>Review the parsed model before importing.</figcaption>
</figure>

## 3. Import the model

Click **Import** and wait for the success message:

```text
Imported 1 model(s) and 0 relationship(s).
```

## 4. Verify the ER diagram

The Modeling page switches to **ER diagram**. Confirm that:

- the Models panel contains one table: `fund_master`;
- the table node shows five columns;
- `fund_code` is marked as the primary key;
- the node shows zero links.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/03-er-diagram-fund-master.png')}
    alt="fund_master table node visible in the ER diagram after import"
  />
  <figcaption>The imported model is visible in the ER diagram.</figcaption>
</figure>

:::warning
Import updates the project's draft modeling state. It does not make the model active for Ask/NL2SQL. Use **Publish** to continue to the artifact snapshot workflow.
:::

## 5. Publish and activate

From **Active Snapshot**, click **Publish**.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/04-publish-entry.png')}
    alt="Active Snapshot page with the Publish button available for the current draft"
  />
  <figcaption>Start the publish flow from Active Snapshot.</figcaption>
</figure>

Review the draft comparison, then click **Publish** in the review modal.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/05-publish-draft-review.png')}
    alt="Publish snapshot modal showing the Current Draft review and Publish button"
  />
  <figcaption>Review the draft before publishing.</figcaption>
</figure>

Confirm the publish action. The dialog explains that the snapshot is activated for live use.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/06-publish-confirm.png')}
    alt="Final Publish snapshot confirmation dialog"
  />
  <figcaption>Confirm publication and activation.</figcaption>
</figure>

## 6. Ask a total-fund question

After the snapshot is published and activated, open the local NL2SQL QA route:

```text
/ai-nl2sql/nl2sql-qa?projectId=demo
```

In **Try It Out**, enter:

```text
How many funds are there in total?
```

Click **Send** to run the question against the active model.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/07-qa-total-fund.png')}
    alt="NL2SQL QA Console with the total-fund question entered and Active Snapshot marked PASS"
  />
  <figcaption>Ask the first question after activation.</figcaption>
</figure>

After **Send** completes, confirm the response card shows **Success**, a confidence score, and the generated SQL. In the local SQL-only demo, `Rows 0 / 0` is expected because no business rows are connected; this step verifies the model-to-SQL response.

<figure>
  <img
    src={useBaseUrl('/img/getting-started/create-import-model/08-qa-response.png')}
    alt="Successful NL2SQL response showing confidence, fund count reasoning, and the generated COUNT SQL"
  />
  <figcaption>Review the final response and generated SQL.</figcaption>
</figure>

:::warning
If the page shows **No active snapshot yet**, finish publishing and activation before submitting the question.
:::
