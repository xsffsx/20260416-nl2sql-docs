---
sidebar_position: 3
title: Semantic Key-Value Mappings
---

# Semantic Key-Value Mappings

Semantic mappings are the bridge between business language and canonical runtime fields.

```text
Key: metric
Value: geographic equity allocation

Key: region.asia_developed
Value: fund_master_view.equity_geographic_allocation_in_asia_developed

Key: region.united_states
Value: fund_master_view.equity_geographic_allocation_in_united_states
```

Keep the mapping explicit. A human can review the business meaning, while the SQL generator receives the exact field binding.
