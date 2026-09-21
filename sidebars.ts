import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'category',
      label: 'Getting Started',
      collapsible: false,
      items: [
        'intro',
        'getting-started/overview',
        'getting-started/local-development',
        'concepts/nl2sql-pipeline',
        'concepts/rag-few-shot',
        'concepts/semantic-key-value-mappings',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      collapsible: false,
      items: ['architecture/langgraph-pipeline', 'architecture/mcp-integration'],
    },
    {
      type: 'category',
      label: 'Runtime Operations',
      collapsed: true,
      items: [
        'runtime/startup-grace',
        'runtime/readiness-liveness',
        'runtime/qa-smoke',
        'runtime/artifact-snapshot',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      collapsed: true,
      items: ['api/health-readiness', 'api/artifact-versions'],
    },
    {
      type: 'category',
      label: 'ADRs',
      collapsed: true,
      items: ['adr/index', 'adr/runtime-boundaries'],
    },
    {
      type: 'category',
      label: 'Troubleshooting',
      collapsed: true,
      items: ['troubleshooting/startup-blocked'],
    },
  ],
};

export default sidebars;
