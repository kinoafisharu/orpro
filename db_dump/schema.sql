[33mBEGIN;[0m
[33mTRUNCATE[0m [32;1m"auth_user"[0m, [32;1m"auth_group"[0m, [32;1m"pages_publish"[0m, [32;1m"pages_headerphoto"[0m, [32;1m"django_content_type"[0m, [32;1m"pages_lblocks"[0m, [32;1m"pages_offers"[0m, [32;1m"pages_mainbaner"[0m, [32;1m"pages_topoffers"[0m, [32;1m"pages_post"[0m, [32;1m"django_admin_log"[0m, [32;1m"thumbnail_kvstore"[0m, [32;1m"pages_reviews"[0m, [32;1m"pages_offers_offer_subtags"[0m, [32;1m"pages_support"[0m, [32;1m"pages_personal"[0m, [32;1m"auth_group_permissions"[0m, [32;1m"pages_tags"[0m, [32;1m"pages_images"[0m, [32;1m"pages_subtags"[0m, [32;1m"django_session"[0m, [32;1m"pages_aboutcompany"[0m, [32;1m"pages_footer"[0m, [32;1m"pages_fblocks"[0m, [32;1m"pages_availability"[0m, [32;1m"auth_user_user_permissions"[0m, [32;1m"pages_category"[0m, [32;1m"auth_permission"[0m, [32;1m"auth_user_groups"[0m;
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"django_admin_log"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"auth_permission"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"auth_group"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"auth_user"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"django_content_type"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_availability"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_publish"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_images"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_category"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_post"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_tags"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_subtags"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_offers"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_mainbaner"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_fblocks"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_lblocks"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_aboutcompany"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_topoffers"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_support"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_personal"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_headerphoto"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_footer"[0m','[32;1mid[0m'), 1, false);
[33mSELECT[0m setval(pg_get_serial_sequence('[1m"pages_reviews"[0m','[32;1mid[0m'), 1, false);
[33mCOMMIT;[0m
