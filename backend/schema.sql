-- ============================================================
-- Gateway Solutions | WhatsApp Tax Office Automation System
-- Database Schema (MySQL 8.0+)
-- ============================================================

DROP DATABASE IF EXISTS gateway_tax_automation;
CREATE DATABASE gateway_tax_automation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE gateway_tax_automation;

-- ------------------------------------------------------------
-- Table: categories
-- Tax compliance categories, e.g. 'Monthly GST', 'Income Tax'
-- ------------------------------------------------------------
CREATE TABLE categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255) DEFAULT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: clients
-- ------------------------------------------------------------
CREATE TABLE clients (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    business_name   VARCHAR(150) NOT NULL,
    contact_name    VARCHAR(100) NOT NULL,
    mobile_number   VARCHAR(20)  NOT NULL UNIQUE COMMENT 'E.164 format e.g. 91XXXXXXXXXX (no + sign, as required by Meta API)',
    gst_details     VARCHAR(20)  DEFAULT NULL,
    pan_details     VARCHAR(15)  DEFAULT NULL,
    tan_details     VARCHAR(15)  DEFAULT NULL,
    category_id     INT DEFAULT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_clients_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: client_categories (Many-to-Many junction table)
-- ------------------------------------------------------------
CREATE TABLE client_categories (
    client_id   INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (client_id, category_id),
    CONSTRAINT fk_client_categories_client
        FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_client_categories_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: compliance_dates
-- Recurring / one-off due dates tied to a category
-- ------------------------------------------------------------
CREATE TABLE compliance_dates (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    due_date    DATE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_compliance_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: invoices
-- ------------------------------------------------------------
CREATE TABLE invoices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    client_id       INT NOT NULL,
    invoice_number  VARCHAR(50) NOT NULL UNIQUE,
    amount          DECIMAL(12,2) NOT NULL,
    service_type    VARCHAR(100) NOT NULL,
    is_sent         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoices_client
        FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table: message_history
-- Log of every WhatsApp message dispatched by the automation engine
-- ------------------------------------------------------------
CREATE TABLE message_history (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    client_id       INT NOT NULL,
    message_type    VARCHAR(50) NOT NULL COMMENT 'e.g. GST_REMINDER, DOCUMENT_REQUEST, BILLING_NOTIFICATION',
    message_content VARCHAR(500) DEFAULT NULL,
    sent_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('PENDING','SENT','FAILED','DELIVERED','READ') NOT NULL DEFAULT 'PENDING',
    CONSTRAINT fk_history_client
        FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Helpful indexes for the scheduler's daily lookups
CREATE INDEX idx_compliance_due_date ON compliance_dates(due_date);
CREATE INDEX idx_clients_category ON clients(category_id);
CREATE INDEX idx_history_sent_timestamp ON message_history(sent_timestamp);
CREATE INDEX idx_history_client ON message_history(client_id);

-- ============================================================
-- DUMMY DATA
-- ============================================================

INSERT INTO categories (name, description) VALUES
('Monthly GST', 'Monthly GSTR-1 / GSTR-3B filing clients'),
('Income Tax', 'Annual Income Tax Return filing clients'),
('TDS', 'Quarterly TDS return filing clients'),
('Quarterly GST (Composition)', 'Composition scheme GST filers');

INSERT INTO clients (business_name, contact_name, mobile_number, gst_details, pan_details, tan_details, category_id, is_active) VALUES
('Sharma Traders',        'Rajesh Sharma',  '919876543210', '27AAAPS1234C1Z5', 'AAAPS1234C', NULL, 1, TRUE),
('Verma Textiles',        'Anita Verma',    '919812345678', '27BBBPT5678D1Z2', 'BBBPT5678D', NULL, 1, TRUE),
('Patiala Auto Parts',    'Gurpreet Singh',  '919898989898', '03CCCPA9876E1Z9', 'CCCPA9876E', 'PTLA12345B', 3, TRUE),
('Kapoor & Associates',   'Neha Kapoor',    '919765432109', NULL,               'DDDPK4567F', NULL, 2, TRUE),
('Singh Electronics',     'Manpreet Singh',  '919911223344', '03EEEPS3344G1Z1', 'EEEPS3344G', NULL, 1, FALSE),
('Bansal Consultancy',    'Deepak Bansal',  '919922334455', NULL,               'FFFPB7890H', 'BNSL54321C', 3, TRUE);

INSERT INTO client_categories (client_id, category_id) VALUES
(1, 1),
(2, 1),
(3, 3),
(4, 2),
(5, 1),
(6, 3);

INSERT INTO compliance_dates (category_id, description, due_date) VALUES
(1, 'GSTR-3B Filing Due Date', DATE_ADD(CURDATE(), INTERVAL 7 DAY)),
(1, 'GSTR-1 Filing Due Date', DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
(3, 'TDS Quarterly Return Due Date', DATE_ADD(CURDATE(), INTERVAL 1 DAY)),
(2, 'Income Tax Return Filing Deadline', DATE_ADD(CURDATE(), INTERVAL 30 DAY));

INSERT INTO invoices (client_id, invoice_number, amount, service_type, is_sent) VALUES
(1, 'INV-2026-001', 2500.00, 'GST Filing Services', TRUE),
(2, 'INV-2026-002', 4500.00, 'GST + Bookkeeping', FALSE),
(3, 'INV-2026-003', 1800.00, 'TDS Return Filing', TRUE),
(4, 'INV-2026-004', 6000.00, 'Income Tax Return', FALSE);

INSERT INTO message_history (client_id, message_type, message_content, status) VALUES
(1, 'GST_REMINDER', 'Reminder: Your GSTR-3B is due in 7 days.', 'SENT'),
(2, 'DOCUMENT_REQUEST', 'Please share your purchase invoices for this month.', 'SENT'),
(3, 'BILLING_NOTIFICATION', 'Invoice INV-2026-003 of Rs. 1800 has been generated.', 'DELIVERED'),
(4, 'GST_REMINDER', 'Reminder: Your Income Tax filing deadline is approaching.', 'FAILED');
