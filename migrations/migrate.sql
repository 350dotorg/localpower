alter table discussions_discussion add column extra_disambiguator varchar(100);
alter table discussions_discussion modify column user_id integer;
alter table discussions_discussion add column mock_user longtext;

alter table actionkit_account add column `random_string` varchar(100);
