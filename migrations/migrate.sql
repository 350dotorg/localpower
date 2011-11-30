alter table geo_point add column `city` varchar(200);
alter table geo_point add column `state` varchar(200);
alter table geo_point add column `country` varchar(200);
alter table geo_point add column `postal` varchar(200);
alter table geo_point add column `raw_data` longtext;

CREATE INDEX `geo_point_28f922ba` ON `geo_point` (`city`);
CREATE INDEX `geo_point_355bfc27` ON `geo_point` (`state`);
CREATE INDEX `geo_point_a9e7aee` ON `geo_point` (`country`);
CREATE INDEX `geo_point_5c389424` ON `geo_point` (`postal`);
