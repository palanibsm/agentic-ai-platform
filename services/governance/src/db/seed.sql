-- Seed data — idempotent (INSERT OR IGNORE)

INSERT OR IGNORE INTO teams (id, name, display_name, description, team_type)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'platform',   'AI Platform Team',       'Core platform managed by AI DevOps',          'platform'),
    ('00000000-0000-0000-0000-000000000002', 'ai-devops',  'AI DevOps',              'Team responsible for AI platform operations',  'ai-devops'),
    ('00000000-0000-0000-0000-000000000003', 'architects', 'AI Architecture Team',   'AI architects with read-only platform access', 'ai-devops');

INSERT OR IGNORE INTO users (id, email, display_name, role, team_id)
VALUES (
    '00000000-0000-0000-0001-000000000001',
    'stels.karthik@gmail.com',
    'Platform Admin',
    'ai-devops',
    '00000000-0000-0000-0000-000000000002'
);
