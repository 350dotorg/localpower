ALTER TABLE `rah_profile` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `rah_profile` ADD CONSTRAINT `geom_id_refs_id_5dc04d7c` FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `groups_group` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `groups_group` ADD CONSTRAINT `geom_id_refs_id_1fbaea70` FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `events_event` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `events_event` ADD CONSTRAINT `geom_id_refs_id_92599a2` FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

CREATE INDEX `rah_profile_7a72f2c0` ON `rah_profile` (`geom_id`);
CREATE INDEX `groups_group_7a72f2c0` ON `groups_group` (`geom_id`);
CREATE INDEX `events_event_7a72f2c0` ON `events_event` (`geom_id`);

