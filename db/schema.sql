CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cooldowns (
    user_id INTEGER NOT NULL,
    command_name TEXT NOT NULL,
    last_used TEXT NOT NULL,
    PRIMARY KEY (user_id, command_name),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    price INTEGER NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    rarity TEXT NOT NULL DEFAULT 'Common',
    usable INTEGER NOT NULL DEFAULT 0,
    consumable INTEGER NOT NULL DEFAULT 0,
    use_message TEXT,
    stock INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_user_id INTEGER,
    type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    organization_type TEXT NOT NULL
        CHECK (
            organization_type IN (
                'BUSINESS',
                'INSTITUTION',
                'GOVERNMENT',
                'FACTION'
            )
        ),
    description TEXT NOT NULL DEFAULT '',
    balance INTEGER NOT NULL DEFAULT 0
        CHECK (balance >= 0),
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL
        CHECK (
            role IN (
                'OWNER',
                'MANAGER',
                'MEMBER'
            )
        ),
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),
    joined_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    removed_at TEXT,
    PRIMARY KEY (
        organization_id,
        user_id
    ),
    FOREIGN KEY (organization_id)
        REFERENCES organizations(organization_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS organization_transactions (
    organization_transaction_id INTEGER
        PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    actor_user_id INTEGER,
    target_user_id INTEGER,
    target_organization_id INTEGER,
    transaction_type TEXT NOT NULL,
    amount INTEGER NOT NULL
        CHECK (amount != 0),
    balance_after INTEGER NOT NULL
        CHECK (balance_after >= 0),
    reason TEXT NOT NULL,
    related_item_id INTEGER,
    reference_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id)
        REFERENCES organizations(organization_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (actor_user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (target_user_id)
        REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (target_organization_id)
        REFERENCES organizations(organization_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (related_item_id)
        REFERENCES shop_items(item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS
    idx_organizations_type_active
ON organizations (
    organization_type,
    active
);

CREATE INDEX IF NOT EXISTS
    idx_organization_members_user_active
ON organization_members (
    user_id,
    active
);

CREATE INDEX IF NOT EXISTS
    idx_organization_members_org_role_active
ON organization_members (
    organization_id,
    role,
    active
);

CREATE INDEX IF NOT EXISTS
    idx_organization_transactions_org_created
ON organization_transactions (
    organization_id,
    created_at DESC
);

CREATE INDEX IF NOT EXISTS
    idx_organization_transactions_actor
ON organization_transactions (
    actor_user_id
);

CREATE INDEX IF NOT EXISTS
    idx_organization_transactions_target_user
ON organization_transactions (
    target_user_id
);

CREATE INDEX IF NOT EXISTS
    idx_organization_transactions_target_org
ON organization_transactions (
    target_organization_id
);

CREATE INDEX IF NOT EXISTS
    idx_organization_transactions_type_created
ON organization_transactions (
    transaction_type,
    created_at DESC
);