CREATE TABLE `groups_groupassociationrequest` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `content_type_id` integer NOT NULL,
    `object_id` integer UNSIGNED NOT NULL,
    `group_id` integer NOT NULL,
    `approved` bool NOT NULL,
    `created` datetime NOT NULL,
    `updated` datetime NOT NULL,
    UNIQUE (`content_type_id`, `object_id`, `group_id`)
)
;
ALTER TABLE `groups_groupassociationrequest` ADD CONSTRAINT `content_type_id_refs_id_1026ce6` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);
ALTER TABLE `groups_groupassociationrequest` ADD CONSTRAINT `group_id_refs_id_ea988031` FOREIGN KEY (`group_id`) REFERENCES `groups_group` (`id`);

CREATE INDEX `groups_groupassociationrequest_e4470c6e` ON `groups_groupassociationrequest` (`content_type_id`);
CREATE INDEX `groups_groupassociationrequest_bda51c3c` ON `groups_groupassociationrequest` (`group_id`);

CREATE TABLE `challenges_challenge_groups` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `challenge_id` integer NOT NULL,
    `group_id` integer NOT NULL,
    UNIQUE (`challenge_id`, `group_id`)
)
;
ALTER TABLE `challenges_challenge_groups` ADD CONSTRAINT `group_id_refs_id_46bf4cfb` FOREIGN KEY (`group_id`) REFERENCES `groups_group` (`id`);
ALTER TABLE `challenges_challenge_groups` ADD CONSTRAINT `challenge_id_refs_id_55f4a245` FOREIGN KEY (`challenge_id`) REFERENCES `challenges_challenge` (`id`);

CREATE TABLE `actions_action_groups` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `action_id` integer NOT NULL,
    `group_id` integer NOT NULL,
    UNIQUE (`action_id`, `group_id`)
)
;
ALTER TABLE `actions_action_groups` ADD CONSTRAINT `group_id_refs_id_5f8dd9a7` FOREIGN KEY (`group_id`) REFERENCES `groups_group` (`id`);
ALTER TABLE `actions_action_groups` ADD CONSTRAINT `action_id_refs_id_749fd18d` FOREIGN KEY (`action_id`) REFERENCES `actions_action` (`id`);
