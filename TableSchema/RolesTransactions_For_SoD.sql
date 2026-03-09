CREATE VIEW [dbo].[RolesTransactions_For_SoD]
AS
    SELECT RolesTransactions.*
    FROM RolesTransactions
        JOIN (
    SELECT DISTINCT SoxGroupsContent.TransactionId
        FROM SoxGroupsContent
) SoxGroupsContent
        ON SoxGroupsContent.TransactionId = RolesTransactions.TransactionId
GO
