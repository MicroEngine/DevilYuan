from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

class DyTreeWidget(QTreeWidget):
    """description of class"""

    def __init__(self, fields, parent=None):
        """
        @fields foramt:
        @fields = [
                    ["level_0_a",
                        [
                            "level_1_a",
                                ["level_2_a", "leaf_id"(optional)],
                                ["level_2_b"]
                        ],
                        ["level_1_b"]
                    ],

                    ["level_0_b",
                        ["level_1_a"],
                        ["level_1_b"]
                    ]
                  ]

        For each leaf, e.g. "level_2" means show name. "leaf_id" means its unique ID in whole @fields, which is optional.
        If "leaf_id" isn't assigned, it will be generated like "level_0_a->level_1_a->1evel_2_a".
        So in same level, show name should be different.
        """
        super().__init__(parent)

        self._fields = fields
        self._leafIdMap = {} # {"leaf_id":tree widget item}, for restore tree item state from config file


        self.__InitFields(self, self._fields)
        self.setHeaderHidden(True)

        self.expandAll()

        self.itemClicked.connect(self.on_itemClicked)
        self.itemChanged.connect(self.on_itemChanged)
        self.currentItemChanged.connect(self.on_currentItemChanged)

    def __GetFieldByShowName(self, fields, name):
        for field in fields:
            if isinstance(field, str):
                if name == field:
                    return fields[1]
            else: # list
                ret =  self.__GetFieldByShowName(field, name)
                if ret != None:
                    return ret

        return None

    def set(self, leafIds):
        """ set leaf's state checked
            @leafIds: []
        """

        for leafId in leafIds:
            if leafId in self._leafIdMap:
                self.__UpdateParent(self._leafIdMap[leafId])

    def __GetFields(self, parent):
        fields = []
        for i in range(parent.childCount()):
            childItem = parent.child(i)

            # leaf
            if childItem.childCount() == 0:
                if childItem.checkState(0) == Qt.Checked:
                    field = self.__GetFieldByShowName(ManualUpdateDialog.Fields, childItem.text(0))
                    fields.append(field)
                continue
            
            if childItem.checkState(0) == Qt.Checked or childItem.checkState(0) == Qt.PartiallyChecked:
                field = self.__GetFields(childItem)
                fields.extend(field)

        return fields


    def __InitFieldItem(self, parent, item):
        treeItem = QTreeWidgetItem(parent)
        treeItem.setText(0, item)
        treeItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        treeItem.setCheckState(0, Qt.Unchecked)

        return treeItem

    def _getLeafId(self, leaf):
        leafId = None
        while leaf is not self and leaf is not None:
            leafId = leaf.text(0) if leafId is None  else leaf.text(0) + "->" + leafId

            leaf = leaf.parent()

        return leafId

    def __InitFields(self, parent, fields):
        for i, field in enumerate(fields):
            if isinstance(field, str):
                if i == 0:
                    parent = self.__InitFieldItem(parent, field)
                else: # leaf ID specified by user
                    self._leafIdMap[field] = parent
            else:
                self.__InitFields(parent, field)

        if i == 0: # dafault leaf ID
            leafId = self._getLeafId(parent)
            if leafId is not None:
                self._leafIdMap[leafId] = parent

    def __UpdateChild(self, parent):
        for i in range(parent.childCount()):
            child = parent.child(i)
            child.setCheckState(0, parent.checkState(0))

            self.__UpdateChild(child)


    def __UpdateParent(self, child):
        parent = child.parent()
        if parent is None or parent is self: return


        partiallySelected = False
        selectedCount = 0
        childCount = parent.childCount()
        for i in range(childCount):
             childItem = parent.child(i)
             if childItem.checkState(0) == Qt.Checked:
                 selectedCount += 1
             elif childItem.checkState(0) == Qt.PartiallyChecked:
                 partiallySelected = True

        if partiallySelected:
            parent.setCheckState(0, Qt.PartiallyChecked)
        else:
            if selectedCount == 0:
                parent.setCheckState(0, Qt.Unchecked)
            elif selectedCount > 0 and selectedCount < childCount:
                parent.setCheckState(0, Qt.PartiallyChecked)
            else:
                parent.setCheckState(0, Qt.Checked)

        self.__UpdateParent(parent)


    def __GetFieldsFromTreeWidget(self):
        fields = self.__GetFields(self.treeWidgetFields.invisibleRootItem())

        return fields


    def __SetFieldsIntoTreeWidget(self, fields):
        if fields:
            self.__SetFields(self.treeWidgetFields.invisibleRootItem(), fields)
    
    def on_itemClicked(self, item, column):
        pass

    def on_currentItemChanged(self, current, previous):
        pass

    def on_itemChanged(self, item, column):
        self.blockSignals(True)

        self.__UpdateChild(item)
        self.__UpdateParent(item)

        self.blockSignals(False)

    def getCheckedTexts(self):

        texts = []
        for _, item in self._leafIdMap.items():
            if item.checkState(0) == Qt.Checked:
                texts.append(item.text(0))

        return texts

    def collapse(self, text):
        items = self.findItems(text, Qt.MatchExactly)
        for item in items:
            self.collapseItem(item)

