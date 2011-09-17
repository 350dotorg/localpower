delete from groups_group where is_geo_group=True;
alter table groups_group drop is_geo_group;
alter table groups_group drop parent_id;
alter table groups_group drop location_type;
