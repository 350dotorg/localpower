delete from groups_group where is_geo_group=True;
alter table groups_group drop is_geo_group;
alter table groups_group drop parent_id;
alter table groups_group drop location_type;

ALTER TABLE `groups_group` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `groups_group` ADD CONSTRAINT `geom_id_refs_id_1fbaea70` 
      FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `rah_profile` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `rah_profile` ADD CONSTRAINT `geom_id_refs_id_5dc04d7c` 
      FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `events_event` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `events_event` ADD CONSTRAINT `geom_id_refs_id_92599a2`
      FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

ALTER TABLE `commitments_contributor` ADD COLUMN `geom_id` INTEGER;
ALTER TABLE `commitments_contributor` ADD CONSTRAINT `geom_id_refs_id_529673fd`
      FOREIGN KEY (`geom_id`) REFERENCES `geo_point` (`id`);

CREATE INDEX `rah_profile_7a72f2c0` ON `rah_profile` (`geom_id`);
CREATE INDEX `groups_group_7a72f2c0` ON `groups_group` (`geom_id`);
CREATE INDEX `events_event_7a72f2c0` ON `events_event` (`geom_id`);
CREATE INDEX `commitments_contributor_7a72f2c0` ON `commitments_contributor` (`geom_id`);