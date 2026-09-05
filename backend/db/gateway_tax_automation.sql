-- phpMyAdmin SQL Dump
-- version 4.5.1
-- http://www.phpmyadmin.net
--
-- Host: 127.0.0.1
-- Generation Time: Sep 05, 2026 at 09:51 AM
-- Server version: 10.1.19-MariaDB
-- PHP Version: 5.5.38

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `gateway_tax_automation`
--

-- --------------------------------------------------------

--
-- Table structure for table `categories`
--

CREATE TABLE `categories` (
  `id` int(11) NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `categories`
--

INSERT INTO `categories` (`id`, `name`, `description`, `created_at`) VALUES
(1, 'Monthly GST', 'Monthly GSTR-1 / GSTR-3B filing clients', '2026-09-04 08:03:00'),
(2, 'Income Tax', 'Annual Income Tax Return filing clients', '2026-09-04 08:03:00'),
(3, 'TDS', 'Quarterly TDS return filing clients', '2026-09-04 08:03:00'),
(4, 'Quarterly GST (Composition)', 'Composition scheme GST filers', '2026-09-04 08:03:00');

-- --------------------------------------------------------

--
-- Table structure for table `clients`
--

CREATE TABLE `clients` (
  `id` int(11) NOT NULL,
  `business_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mobile_number` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'E.164 format e.g. 91XXXXXXXXXX (no + sign, as required by Meta API)',
  `gst_details` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pan_details` varchar(15) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `category_id` int(11) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `clients`
--

INSERT INTO `clients` (`id`, `business_name`, `contact_name`, `mobile_number`, `gst_details`, `pan_details`, `category_id`, `is_active`, `created_at`, `updated_at`) VALUES
(1, 'Sharma Traders', 'Rajesh Sharma', '919876543210', '27AAAPS1234C1Z5', 'AAAPS1234C', 1, 1, '2026-09-04 08:03:00', '2026-09-04 08:03:00'),
(2, 'Verma Textiles', 'Sangeeta Verma', '919812345678', '27BBBPT5678D1Z2', 'BBBPT5678D', 1, 1, '2026-09-04 08:03:00', '2026-09-05 07:45:54'),
(3, 'Patiala Auto Parts', 'Gurpreet Singh', '919898989898', '03CCCPA9876E1Z9', 'CCCPA9876E', 3, 1, '2026-09-04 08:03:00', '2026-09-04 08:03:00'),
(4, 'Kapoor & Associates', 'Neha Kapoor', '919765432109', NULL, 'DDDPK4567F', 2, 1, '2026-09-04 08:03:00', '2026-09-04 08:03:00'),
(5, 'Singh Electronics', 'Manpreet Singh', '919911223344', '03EEEPS3344G1Z1', 'EEEPS3344G', 1, 0, '2026-09-04 08:03:00', '2026-09-04 08:03:00'),
(6, 'Bansal Consultancy', 'Deepak Bansal', '919922334455', NULL, 'FFFPB7890H', 3, 1, '2026-09-04 08:03:00', '2026-09-04 08:03:00');

-- --------------------------------------------------------

--
-- Table structure for table `compliance_dates`
--

CREATE TABLE `compliance_dates` (
  `id` int(11) NOT NULL,
  `category_id` int(11) NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `due_date` date NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `compliance_dates`
--

INSERT INTO `compliance_dates` (`id`, `category_id`, `description`, `due_date`, `created_at`) VALUES
(1, 1, 'GSTR-3B Filing Due Date', '2026-09-11', '2026-09-04 08:03:00'),
(2, 1, 'GSTR-1 Filing Due Date', '2026-09-07', '2026-09-04 08:03:00'),
(3, 3, 'TDS Quarterly Return Due Date', '2026-09-05', '2026-09-04 08:03:00'),
(4, 2, 'Income Tax Return Filing Deadline', '2026-10-04', '2026-09-04 08:03:00');

-- --------------------------------------------------------

--
-- Table structure for table `invoices`
--

CREATE TABLE `invoices` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `invoice_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(12,2) NOT NULL,
  `service_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_sent` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `invoices`
--

INSERT INTO `invoices` (`id`, `client_id`, `invoice_number`, `amount`, `service_type`, `is_sent`, `created_at`) VALUES
(1, 1, 'INV-2026-001', '2500.00', 'GST Filing Services', 1, '2026-09-04 08:03:00'),
(2, 2, 'INV-2026-002', '4500.00', 'GST + Bookkeeping', 0, '2026-09-04 08:03:00'),
(3, 3, 'INV-2026-003', '1800.00', 'TDS Return Filing', 1, '2026-09-04 08:03:00'),
(4, 4, 'INV-2026-004', '6000.00', 'Income Tax Return', 0, '2026-09-04 08:03:00');

-- --------------------------------------------------------

--
-- Table structure for table `message_history`
--

CREATE TABLE `message_history` (
  `id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `message_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'e.g. GST_REMINDER, DOCUMENT_REQUEST, BILLING_NOTIFICATION',
  `message_content` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sent_timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('PENDING','SENT','FAILED','DELIVERED','READ') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `message_history`
--

INSERT INTO `message_history` (`id`, `client_id`, `message_type`, `message_content`, `sent_timestamp`, `status`) VALUES
(1, 1, 'GST_REMINDER', 'Reminder: Your GSTR-3B is due in 7 days.', '2026-09-04 08:03:00', 'SENT'),
(2, 2, 'DOCUMENT_REQUEST', 'Please share your purchase invoices for this month.', '2026-09-04 08:03:00', 'SENT'),
(3, 3, 'BILLING_NOTIFICATION', 'Invoice INV-2026-003 of Rs. 1800 has been generated.', '2026-09-04 08:03:00', 'DELIVERED'),
(4, 4, 'GST_REMINDER', 'Reminder: Your Income Tax filing deadline is approaching.', '2026-09-04 08:03:00', 'FAILED');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `categories`
--
ALTER TABLE `categories`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `clients`
--
ALTER TABLE `clients`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `mobile_number` (`mobile_number`),
  ADD KEY `idx_clients_category` (`category_id`);

--
-- Indexes for table `compliance_dates`
--
ALTER TABLE `compliance_dates`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_compliance_category` (`category_id`),
  ADD KEY `idx_compliance_due_date` (`due_date`);

--
-- Indexes for table `invoices`
--
ALTER TABLE `invoices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `invoice_number` (`invoice_number`),
  ADD KEY `fk_invoices_client` (`client_id`);

--
-- Indexes for table `message_history`
--
ALTER TABLE `message_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_history_sent_timestamp` (`sent_timestamp`),
  ADD KEY `idx_history_client` (`client_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `categories`
--
ALTER TABLE `categories`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
--
-- AUTO_INCREMENT for table `clients`
--
ALTER TABLE `clients`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;
--
-- AUTO_INCREMENT for table `compliance_dates`
--
ALTER TABLE `compliance_dates`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
--
-- AUTO_INCREMENT for table `invoices`
--
ALTER TABLE `invoices`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
--
-- AUTO_INCREMENT for table `message_history`
--
ALTER TABLE `message_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
--
-- Constraints for dumped tables
--

--
-- Constraints for table `clients`
--
ALTER TABLE `clients`
  ADD CONSTRAINT `fk_clients_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL ON UPDATE CASCADE;

--
-- Constraints for table `compliance_dates`
--
ALTER TABLE `compliance_dates`
  ADD CONSTRAINT `fk_compliance_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `invoices`
--
ALTER TABLE `invoices`
  ADD CONSTRAINT `fk_invoices_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `message_history`
--
ALTER TABLE `message_history`
  ADD CONSTRAINT `fk_history_client` FOREIGN KEY (`client_id`) REFERENCES `clients` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
