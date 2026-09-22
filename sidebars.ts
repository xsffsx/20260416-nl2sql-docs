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
        'getting-started/create-import-model',
        'concepts/why_wdv_nl2sql',
        'concepts/nl2sql-pipeline',
        'concepts/rag-few-shot',
        'concepts/semantic-key-value-mappings',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      collapsible: false,
      items: ['architecture/overview', 'architecture/mcp-integration'],
    },
    {
      type: 'category',
      label: 'Runtime Operations',
      collapsed: true,
      items: [
        'runtime/startup-readiness',
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
