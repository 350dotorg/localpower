ALTER TABLE `rah_profile` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `rah_profile` ADD CONSTRAINT `geom_id_refs_id_5dc04d7c` FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `groups_group` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `groups_group` ADD CONSTRAINT `geom_id_refs_id_1fbaea70` FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

