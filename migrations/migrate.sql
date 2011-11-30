ALTER TABLE `geo_point` ADD COLUMN `region` varchar(200);
CREATE INDEX `geo_point_22f80acf` ON `geo_point` (`region`);
