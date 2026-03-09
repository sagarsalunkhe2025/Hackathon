CREATE TABLE [dbo].[RoleToRoleMappingRules]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [OriginalRoleId] bigint NOT NULL,
    [AdditionalRoleId] bigint NOT NULL,
    [Remerks] nvarchar(200) NULL,
    [RoleToRoleMappingStrategieId] bigint NULL
);
