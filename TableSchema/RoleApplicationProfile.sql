CREATE TABLE [dbo].[RoleApplicationProfile]
(
    [UserId] bigint NOT NULL,
    [LastUse] datetime NOT NULL,
    [RoleName] nvarchar(400) NOT NULL,
    [LastUseLocalTime] datetime NOT NULL
);
