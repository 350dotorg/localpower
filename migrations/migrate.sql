alter table actions_action add is_group_project bool NOT NULL;
CREATE INDEX `actions_action_171b4c55` ON `actions_action` (`is_group_project`);
